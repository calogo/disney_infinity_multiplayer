// DI3 Local Co-op mod — proxy bink2w32.dll
// Reenvia todos los exports al bink2w32 original (renombrado _bink2w32_orig.dll)
// y lanza un hilo que, al pulsar START en el mando 2, activa el co-op local.
// Solo memoria del proceso en runtime. No toca saves, red ni logros. Reversible.
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>

#define XI_START 0x0010

static HINSTANCE g_self;
static char g_log[MAX_PATH];

static void L(const char* fmt, ...){
    FILE* f = fopen(g_log, "a");
    if(!f) return;
    va_list ap; va_start(ap, fmt); vfprintf(f, fmt, ap); va_end(ap);
    fputc('\n', f); fclose(f);
}

// ============================ SECUENCIA CO-OP ============================
// Direcciones probadas (ImageBase 0x400000; se rebasan al modulo del juego).
#define RVA(x) ((x) - 0x400000)
static void* game_base(void){ return (void*)GetModuleHandleA(NULL); }
static DWORD gp(void* base, DWORD ghidra){ return (DWORD)((BYTE*)base + RVA(ghidra)); }

// scan de heap para el gameLoop (mismo patron que el script Frida)
static void* find_gameloop(void* base){
    DWORD vt0  = gp(base, 0x1D4418C);
    DWORD vt58 = gp(base, 0x1D44180);
    DWORD vt308= gp(base, 0x1D44174);
    DWORD vt378= gp(base, 0x1D43F88);
    MEMORY_BASIC_INFORMATION mbi;
    BYTE* p = NULL;
    while(VirtualQuery(p, &mbi, sizeof(mbi)) == sizeof(mbi)){
        BYTE* region = (BYTE*)mbi.BaseAddress;
        SIZE_T sz = mbi.RegionSize;
        if(mbi.State==MEM_COMMIT && !(mbi.Protect & (PAGE_GUARD|PAGE_NOACCESS)) &&
           (mbi.Protect==PAGE_READWRITE || mbi.Protect==PAGE_WRITECOPY)){
            for(SIZE_T off=0; off+0x37C <= sz; off+=4){
                if(*(DWORD*)(region+off) == vt0){
                    BYTE* o = region+off;
                    if(*(DWORD*)(o+0x58)==vt58 && *(DWORD*)(o+0x308)==vt308 && *(DWORD*)(o+0x378)==vt378)
                        return o;
                }
            }
        }
        p = region + sz;
    }
    return NULL;
}

typedef void (__thiscall *dropin_t)(void*, int);
static int g_coop_done = 0;
static int g_active = 0;         // materializacion activa (tras drop-in)
static int g_hooks_done = 0;

// ---- carga de modelo del personaje de P2 (ruta ActivateChanges) ----
// FUN_00b73060(this=*(DAT_0221ceb8), playerId, itemPtr, force) aplica + carga el modelo.
// item ES UN PUNTERO al objeto de catalogo (item+0xC8 = sku, item+0xD0 -> nombre).
typedef void (__thiscall *applychar_t)(void* self, int playerId, void* item, int force);
static void* g_p2_item = 0;      // puntero de item resuelto para el sku actual de P2
static void* g_pending_item = 0; // item a aplicar (lo consume el hook e01890)
static int   g_cycle_pending = 0;// 1 = re-materializar el cuerpo de P2 con el nuevo personaje
static int mem_ok(void* p, SIZE_T n, int write);   // (definida mas abajo)

// ---- lista para el CAMBIADOR de personaje de P2 (Star Wars primero) ----
typedef struct { const char* name; DWORD sku; } chardef_t;
static const chardef_t g_chars[] = {
    {"Ahsoka",0xf430b},{"Anakin",0xf4308},{"ObiWan",0xf4309},{"Yoda",0xf430a},{"DarthMaul",0xf430c},
    {"Luke",0xf430e},{"HanSolo",0xf430f},{"Leia",0xf4310},{"Chewbacca",0xf4311},{"Vader",0xf4312},{"BobaFett",0xf4313},
    {"Ezra",0xf4314},{"Kanan",0xf4315},{"Sabine",0xf4316},{"Zeb",0xf4317},
    {"CaptainAmerica",0xf42a4},{"Hulk",0xf42a5},{"Ironman",0xf42a6},{"Spiderman",0xf42ab},{"Thor",0xf42a7},
    {"BlackPanther",0xf4336},{"Groot",0xf42a8},{"Rocket",0xf42a9},{"Venom",0xf42b3},
    {"ClassicMickey",0xf431d},{"Elsa",0xf4259},{"Aladdin",0xf42b5},{"Stitch",0xf42b6},{"Maleficent",0xf42b9},
    {"JackSparrow",0xf4243},{"Woody",0xf4250},{"Buzz",0xf4248},{"Mulan",0xf431f},
};
#define NCHARS (int)(sizeof(g_chars)/sizeof(g_chars[0]))
static void* g_items_cache[NCHARS] = {0};   // puntero de item por personaje (resuelto una vez)
static int   g_cyc_idx = 0;

// resuelve sku -> puntero del item de catalogo (escaneo; correr en hilo worker)
static void* resolve_item_ptr(DWORD sku){
    MEMORY_BASIC_INFORMATION mbi;
    BYTE* p = 0;
    while(VirtualQuery(p, &mbi, sizeof(mbi)) == sizeof(mbi)){
        BYTE* region = (BYTE*)mbi.BaseAddress;
        SIZE_T sz = mbi.RegionSize;
        if(mbi.State==MEM_COMMIT && !(mbi.Protect & (PAGE_GUARD|PAGE_NOACCESS)) &&
           (mbi.Protect==PAGE_READWRITE || mbi.Protect==PAGE_WRITECOPY)){
            BYTE* it;
            for(it = region; it + 0xE0 <= region + sz; it += 4){
                if(*(DWORD*)(it + 0xC8) == sku){
                    DWORD nameptr = *(DWORD*)(it + 0xD0);
                    if(nameptr > 0x10000){
                        MEMORY_BASIC_INFORMATION m2;
                        if(VirtualQuery((void*)nameptr, &m2, sizeof(m2))==sizeof(m2) &&
                           m2.State==MEM_COMMIT && !(m2.Protect & (PAGE_GUARD|PAGE_NOACCESS))){
                            BYTE c0 = *(BYTE*)nameptr;
                            if(c0 >= 0x20 && c0 < 0x7f) return it;   // item valido
                        }
                    }
                }
            }
        }
        p = region + sz;
    }
    return 0;
}

// resuelve TODOS los items de g_chars[] en una sola pasada (para el cambiador)
static void prescan_items(void){
    MEMORY_BASIC_INFORMATION mbi;
    BYTE* p = 0;
    while(VirtualQuery(p, &mbi, sizeof(mbi)) == sizeof(mbi)){
        BYTE* region = (BYTE*)mbi.BaseAddress;
        SIZE_T sz = mbi.RegionSize;
        if(mbi.State==MEM_COMMIT && !(mbi.Protect & (PAGE_GUARD|PAGE_NOACCESS)) &&
           (mbi.Protect==PAGE_READWRITE || mbi.Protect==PAGE_WRITECOPY)){
            BYTE* it;
            for(it = region; it + 0xE0 <= region + sz; it += 4){
                DWORD sku = *(DWORD*)(it + 0xC8);
                if(sku >= 0xf4000 && sku < 0xf5000){
                    DWORD nameptr = *(DWORD*)(it + 0xD0);
                    if(nameptr > 0x10000 && mem_ok((void*)nameptr, 1, 0) &&
                       (*(BYTE*)nameptr) >= 0x20 && (*(BYTE*)nameptr) < 0x7f){
                        for(int i=0;i<NCHARS;i++)
                            if(!g_items_cache[i] && g_chars[i].sku==sku){ g_items_cache[i]=it; break; }
                    }
                }
            }
        }
        p = region + sz;
    }
    int found=0; for(int i=0;i<NCHARS;i++) if(g_items_cache[i]) found++;
    L("[coop] cambiador: %d/%d personajes resueltos", found, NCHARS);
}

#define P2_SKU_DEFAULT 0xf431d   // Mickey (por defecto)
#define POSX   0x10000
static DWORD g_p2_sku = P2_SKU_DEFAULT;

// Lee el SKU del personaje de P2 desde  coop_p2.txt  (junto al DLL).
// Formato: un numero hex, p.ej.  0xf431d   o   f431d   (Mickey).
static void read_p2_sku(void){
    char path[MAX_PATH];
    lstrcpynA(path, g_log, MAX_PATH);
    char* p = strrchr(path, '\\');
    if(p) strcpy(p+1, "coop_p2.txt"); else strcpy(path, "coop_p2.txt");
    FILE* f = fopen(path, "r");
    if(!f){ L("[coop] sin coop_p2.txt -> P2 = Mickey (0x%x)", g_p2_sku); return; }
    char buf[64] = {0};
    if(fgets(buf, sizeof(buf), f)){
        unsigned long v = strtoul(buf, NULL, 16);   // acepta "0xNNNN" o "NNNN"
        if(v != 0 && v != 0xfffffffful) g_p2_sku = (DWORD)v;
    }
    fclose(f);
    L("[coop] P2 SKU (coop_p2.txt) = 0x%x", g_p2_sku);
}

// ---- infra de hooks inline (trampolin) ----
void* g_tramp_e01890 = 0;
void* g_tramp_solidify = 0;

static void* install_hook(void* target, void* detour, int copylen){
    BYTE* tramp = (BYTE*)VirtualAlloc(0, copylen + 5, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if(!tramp) return 0;
    memcpy(tramp, target, copylen);
    tramp[copylen] = 0xE9;
    *(DWORD*)(tramp + copylen + 1) = (DWORD)((BYTE*)target + copylen) - (DWORD)(tramp + copylen + 5);
    DWORD old;
    VirtualProtect(target, copylen, PAGE_EXECUTE_READWRITE, &old);
    ((BYTE*)target)[0] = 0xE9;
    *(DWORD*)((BYTE*)target + 1) = (DWORD)detour - ((DWORD)target + 5);
    for(int i=5;i<copylen;i++) ((BYTE*)target)[i] = 0x90;
    VirtualProtect(target, copylen, old, &old);
    FlushInstructionCache(GetCurrentProcess(), target, copylen);
    return tramp;
}

// ---- materializacion (corre dentro de e01890, mgr=ecx) ----
static int g_frames = 0, g_newHandle = 0, g_joinMsg = 0;
void on_e01890(void* mgr){
    if(!g_active || !mgr) return;
    // CAMBIO DE PERSONAJE: re-materializar el cuerpo de P2 con el nuevo sku
    if(g_cycle_pending){
        g_cycle_pending = 0;
        g_frames = 0; g_newHandle = 0; g_joinMsg = 0;
        *(DWORD*)((BYTE*)mgr + 0x64) = 0;      // borrar handle -> FASE1 re-fuerza el spawn
        *((BYTE*)mgr + 0x845) = 0;             // des-congelar
        g_pending_item = g_p2_item;            // tras re-materializar, cargar su modelo
        L("[coop] re-materializando P2 (nuevo personaje sku 0x%x)...", g_p2_sku);
    }
    g_frames++;
    void* base = game_base();
    *(DWORD*)((BYTE*)base + 0x1E0191C) = 1;               // introFlag
    void* g = *(void**)((BYTE*)base + 0x1E5F540);          // gCountPtr -> g
    if(g){ if(*(DWORD*)((BYTE*)g + 0x94) < 2) *(DWORD*)((BYTE*)g + 0x94) = 2; }
    if(g_newHandle == 0){ DWORD hx = *(DWORD*)((BYTE*)mgr + 0x64); if(hx > 0x100000 && hx != 0xffffffff) g_newHandle = hx; }
    if(g_newHandle == 0 && g_frames < 45){
        void* pA = *(void**)((BYTE*)mgr + 0xC);
        void* pB = *(void**)((BYTE*)mgr + 0x8);
        if(pA){ *(DWORD*)((BYTE*)pA+0x10)=g_p2_sku; *(DWORD*)((BYTE*)pA+0x58)=POSX; *(DWORD*)((BYTE*)pA+0x5C)=0; }
        if(pB){ *(DWORD*)((BYTE*)pB+0x10)=0; *(DWORD*)((BYTE*)pB+0x58)=0; *(DWORD*)((BYTE*)pB+0x5C)=0; }
        *((BYTE*)mgr+0x845)=0; *((BYTE*)mgr+0x880)=0; *((BYTE*)mgr+0x88c)=0;
        *((BYTE*)mgr+0x84b)=0; *((BYTE*)mgr+0x84c)=0;
        *((BYTE*)mgr+0x867)=1; *((BYTE*)mgr+0x83a)=1;
        if(*(int*)((BYTE*)mgr+0xcc) == -1 && g){
            void* ctxArr = *(void**)((BYTE*)g + 0x108);
            if(ctxArr){ void* ctx1 = (BYTE*)ctxArr + 0x50;
                *(DWORD*)((BYTE*)ctx1+0x10)=1; *(DWORD*)((BYTE*)ctx1+0x48)=1;
                *((BYTE*)ctx1+0x20) = *((BYTE*)ctxArr+0x20);
                *(DWORD*)((BYTE*)mgr+0xcc)=1;
            }
        }
    } else {
        *((BYTE*)mgr+0x845)=1; *((BYTE*)mgr+0x83a)=0;   // CONGELAR (cuerpo solido)
        if(!g_joinMsg){ g_joinMsg=1; L("[coop] CONGELADO (cuerpo solido). frames=%d", g_frames); }
        // aplicar/cambiar el personaje de P2 cuando hay uno pendiente (inicial o cambiador)
        if(g_pending_item){
            void* it = g_pending_item; g_pending_item = 0;
            void* self = *(void**)((BYTE*)base + 0x1E1CEB8);   // *(DAT_0221ceb8)
            if(mem_ok(self, 0x40, 0)){
                applychar_t fn = (applychar_t)((BYTE*)base + 0x773060); // FUN_00b73060
                fn(self, 1, it, 1);   // playerId=1 (P2), force=1
                L("[coop] applyChar P2 -> item=%p", it);
            } else L("[coop] applyChar: self no valido");
        }
    }
}

// ---- solidificar avatar slot 1 (dentro de 9e9dc0; args en pila) ----
void on_solidify(void* esp){
    DWORD slot = *(DWORD*)((BYTE*)esp + 4);
    void* av   = *(void**)((BYTE*)esp + 8);
    if(slot == 1 && av){ BYTE f = *((BYTE*)av + 0x39); if(f & 2) *((BYTE*)av + 0x39) = f & 0xFD; }
}

__attribute__((naked)) void stub_e01890(void){
    __asm__(
        "pushal\n\t"
        "pushfl\n\t"
        "pushl %ecx\n\t"
        "call _on_e01890\n\t"
        "addl $4, %esp\n\t"
        "popfl\n\t"
        "popal\n\t"
        "jmp *_g_tramp_e01890\n\t"
    );
}
__attribute__((naked)) void stub_solidify(void){
    __asm__(
        "pushal\n\t"
        "pushfl\n\t"
        "leal 36(%esp), %eax\n\t"
        "pushl %eax\n\t"
        "call _on_solidify\n\t"
        "addl $4, %esp\n\t"
        "popfl\n\t"
        "popal\n\t"
        "jmp *_g_tramp_solidify\n\t"
    );
}

static void install_hooks(void* base){
    if(g_hooks_done) return;
    g_tramp_e01890  = install_hook((BYTE*)base + 0xA01890, (void*)stub_e01890, 6);
    g_tramp_solidify= install_hook((BYTE*)base + 0x9E9DC0, (void*)stub_solidify, 7);
    g_hooks_done = 1;
    L("[coop] hooks instalados: e01890=%p solidify=%p", g_tramp_e01890, g_tramp_solidify);
}

// comprobar que [p, p+n) es memoria commit legible (write=1 => escribible)
static int mem_ok(void* p, SIZE_T n, int write){
    MEMORY_BASIC_INFORMATION mbi;
    if(!p) return 0;
    if(VirtualQuery(p, &mbi, sizeof(mbi)) != sizeof(mbi)) return 0;
    if(mbi.State != MEM_COMMIT) return 0;
    if(mbi.Protect & (PAGE_GUARD|PAGE_NOACCESS)) return 0;
    DWORD pr = mbi.Protect & 0xFF;
    int rd = (pr==PAGE_READONLY||pr==PAGE_READWRITE||pr==PAGE_WRITECOPY||
              pr==PAGE_EXECUTE_READ||pr==PAGE_EXECUTE_READWRITE||pr==PAGE_EXECUTE_WRITECOPY);
    int wr = (pr==PAGE_READWRITE||pr==PAGE_WRITECOPY||
              pr==PAGE_EXECUTE_READWRITE||pr==PAGE_EXECUTE_WRITECOPY);
    if((BYTE*)p + n > (BYTE*)mbi.BaseAddress + mbi.RegionSize) return 0;
    return write ? wr : rd;
}

static void run_coop(void){
    if(g_coop_done) return;
    void* base = game_base();
    L("[coop] base=%p", base);

    // OJO: las direcciones de CODIGO ya son RVA (offset desde base), NO se les resta 0x400000.
    // Solo las vtables (find_gameloop) son VA de Ghidra.
    void* pOperand = (BYTE*)base + (0x69E3CF + 2);
    if(!mem_ok(pOperand, 4, 0)){ L("[coop] operando @%p no legible", pOperand); return; }
    DWORD opAddr = *(DWORD*)pOperand;
    L("[coop] opAddr(global)=%08x", opAddr);

    if(!mem_ok((void*)opAddr, 4, 0)){ L("[coop] global @%08x no legible (no estas en partida?)", opAddr); return; }
    void* gamePlayers = *(void**)opAddr;
    L("[coop] gamePlayers=%p", gamePlayers);
    if(!mem_ok(gamePlayers, 0x100, 1)){ L("[coop] gamePlayers no escribible -> entra a una Toy Box y reintenta"); return; }

    *((BYTE*)gamePlayers + 0x98) = 1;
    L("[coop] +0x98=1 OK, buscando gameLoop...");

    void* gameLoop = find_gameloop(base);
    if(!gameLoop){ L("[coop] gameLoop NO encontrado (reintenta con Start)"); return; }
    L("[coop] gameLoop=%p -> DROP-IN", gameLoop);

    read_p2_sku();                       // personaje de P2 desde coop_p2.txt
    install_hooks(base);                 // hooks activos ANTES del drop-in

    dropin_t dropInFn = (dropin_t)((BYTE*)base + 0x69B020);  // RVA (no restar 0x400000)
    *((BYTE*)gamePlayers + 0x98) = 1;
    dropInFn(gameLoop, 1);
    g_coop_done = 1;
    g_active = 1;                         // e01890 empieza a materializar a P2
    L("[coop] drop-in llamado + materializacion ON. P2 solido en ~1s.");
    // resolver TODOS los personajes del cambiador (una pasada) + el inicial
    prescan_items();
    // colocar el indice del cambiador en el personaje inicial (si esta en la lista)
    for(int i=0;i<NCHARS;i++) if(g_chars[i].sku==g_p2_sku){ g_cyc_idx=i; break; }
    g_p2_item = (g_cyc_idx>=0 && g_items_cache[g_cyc_idx]) ? g_items_cache[g_cyc_idx]
                                                          : resolve_item_ptr(g_p2_sku);
    g_pending_item = g_p2_item;    // aplicar el personaje inicial una vez
    L("[coop] item inicial de P2 (sku 0x%x) = %p", g_p2_sku, g_p2_item);
}
// =========================================================================

typedef DWORD (WINAPI *XInputGetState_t)(DWORD, void*);
static XInputGetState_t pXI = NULL;

static void load_xinput(void){
    const char* dlls[] = {"xinput1_4.dll","xinput1_3.dll","xinput9_1_0.dll","xinput1_2.dll","xinput1_1.dll"};
    for(int i=0;i<5;i++){
        HMODULE m = LoadLibraryA(dlls[i]);
        if(m){ pXI = (XInputGetState_t)GetProcAddress(m, "XInputGetState");
               if(pXI){ L("[xinput] %s", dlls[i]); return; } }
    }
    L("[xinput] NO encontrado");
}

static void coop_trigger(void){
    L("[coop] START en mando 2 -> lanzando secuencia co-op");
    run_coop();
}

static DWORD WINAPI worker(LPVOID unused){
    (void)unused;
    Sleep(1500);
    L("=== DI3 co-op mod cargado (proxy bink2w32) ===");
    load_xinput();
    BYTE prev[4] = {0,0,0,0};
    BYTE prevCyc[4] = {0,0,0,0};
    for(;;){
        if(pXI){
            for(DWORD pad=0; pad<4; pad++){
                BYTE st[16];
                if(pXI(pad, st) == ERROR_SUCCESS){
                    WORD b = *(WORD*)(st+4);
                    BYTE now = (b & XI_START) ? 1 : 0;
                    if(now && !prev[pad]){
                        L("[input] START en pad %lu", pad);
                        if(pad == 1) coop_trigger();
                    }
                    prev[pad] = now;
                    // CAMBIADOR de personaje de P2: LB+RB juntos en el mando 2 (pad 1)
                    BYTE cyc = ((b & 0x0300) == 0x0300) ? 1 : 0;   // LEFT_SHOULDER|RIGHT_SHOULDER
                    if(cyc && !prevCyc[pad] && pad == 1 && g_active && !g_cycle_pending){
                        for(int k=0; k<NCHARS; k++){
                            g_cyc_idx = (g_cyc_idx + 1) % NCHARS;
                            if(g_items_cache[g_cyc_idx]){
                                g_p2_sku  = g_chars[g_cyc_idx].sku;   // FASE1 usara este sku
                                g_p2_item = g_items_cache[g_cyc_idx]; // para cargar su modelo
                                g_cycle_pending = 1;                  // el hook re-materializa
                                L("[input] cambiar P2 -> %s (0x%x)", g_chars[g_cyc_idx].name, g_chars[g_cyc_idx].sku);
                                break;
                            }
                        }
                    }
                    prevCyc[pad] = cyc;
                }
            }
        }
        Sleep(25);
    }
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r){
    (void)r;
    if(reason == DLL_PROCESS_ATTACH){
        g_self = h;
        GetModuleFileNameA(h, g_log, MAX_PATH);
        char* p = strrchr(g_log, '\\');
        if(p) strcpy(p+1, "di3_coop.log"); else strcpy(g_log, "di3_coop.log");
        DeleteFileA(g_log);
        DisableThreadLibraryCalls(h);
        CreateThread(NULL, 0, worker, NULL, 0, NULL);
    }
    return TRUE;
}
