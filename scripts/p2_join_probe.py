import frida, time

# ============================================================================
# SONDA JOIN P2 (via nativa) — Sesion 12
# Hooks (Ghidra base 0x400000 -> RVA = Ghidra - 0x400000; runtime = base + RVA):
#   FUN_00deb350 (RVA 0x9eb350) = handler "entra el Jugador 2" (-> IGP_PlaceAvatarP2)
#   FUN_00ddae30 (RVA 0x9dae30) = VALIDADOR del join (return 1=ok/0=no, *param_4=codigo)
#   FUN_00fdc180 (RVA 0xbdc180) = UI popups (loguea si es IGP/P2/Avatar/Join)
# Objetivo: pulsar START en el 2o mando dentro de un toybox y ver si salta el join.
# ============================================================================

PROC = "DisneyInfinity3.exe"
print("Esperando el juego (lanzalo desde Steam)...", flush=True)
while True:
    try: session = frida.attach(PROC); break
    except frida.ProcessNotFoundError: time.sleep(0.2)
print("Enganchado. Instalando hooks del join P2...", flush=True)

JS = r'''
var EXE=null; var mods=Process.enumerateModules();
for(var i=0;i<mods.length;i++){ if(/DisneyInfinity3\.exe/i.test(mods[i].name)){EXE=mods[i];break;} }
if(!EXE) EXE=mods[0];
send("[i] base="+EXE.base);
function A(rva){ return EXE.base.add(rva); }

// FUN_00deb350  (thiscall: this=ecx, param_2=[esp+4]=a[0])
Interceptor.attach(A(0x9eb350), {
  onEnter:function(a){
    send(">>> [P2-JOIN] FUN_00deb350 disparada!  this="+this.context.ecx+" param2="+a[0]+
         "   (el juego esta procesando 'entra el Jugador 2')");
  }
});

// FUN_00ddae30 validador (thiscall: this=ecx; a[0]=p2 a[1]=tag a[2]=int*err a[3]=p5 a[4]=p6)
Interceptor.attach(A(0x9dae30), {
  onEnter:function(a){
    this.pErr=a[2];
    send(">>> [VALIDA] FUN_00ddae30  this="+this.context.ecx+" tag="+a[1]+" pErr="+a[2]);
  },
  onLeave:function(r){
    var err="?"; try{ if(!this.pErr.isNull()) err=this.pErr.readS32(); }catch(e){}
    send("    [VALIDA] return="+(r.toInt32()&0xff)+"  errCode="+err+
         "   (0=OK entra; 4/6/7/8/9=rechazo con motivo)");
  }
});

// FUN_00fdc180 UI popup (thiscall: this=ecx; a[0]=p2 a[1]=puntero-a-string-cmd)
Interceptor.attach(A(0xbdc180), {
  onEnter:function(a){
    try{ var s=a[1].readPointer().readCString();
      if(s && /IGP|P2|Avatar|Join|Missing/i.test(s)) send(">>> [UI] popup cmd=\""+s+"\"");
    }catch(e){}
  }
});

send("[ok] Hooks listos. Entra a un TOYBOX con el Jugador 1 y pulsa START en el 2o mando.");
'''

def on_msg(m, d):
    print(m['payload'] if m['type']=='send' else m, flush=True)

s = session.create_script(JS); s.on('message', on_msg); s.load()
print("== corriendo ==", flush=True)
try:
    while True: time.sleep(0.5)
except KeyboardInterrupt: pass
