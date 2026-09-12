import frida, time

# ============================================================================
# JOIN NATURAL (popup + Start) + PANTALLA PARTIDA + CÁMARA  (Sesión 10)
# ----------------------------------------------------------------------------
# NUEVO ENFOQUE (idea del usuario, ataca la RAÍZ):
#   Los intentos previos FORZABAN el avatar directamente -> se saltaban el flujo
#   de "unirse", así que el juego NUNCA asignaba el mando al jugador 2 NI le daba
#   objetivo a la cámara. TODO está ligado al "jugador local" que nace al pulsar Start.
#   Por eso: 1) hacemos salir el POPUP nativo "pulsa Start para unirte";
#            2) el jugador 2 pulsa START -> el juego asigna el mando de forma natural;
#            3) SOLO ENTONCES completamos el avatar + partimos la pantalla + arreglamos
#               la cámara, para que mando+cámara+avatar se cableen juntos.
# ----------------------------------------------------------------------------
# PROCEDIMIENTO DE PRUEBA:
#   1. Estar dentro del Toy Box, estable.
#   2. Lanzar el script. En ~2s debería salir el POPUP de "pulsa Start".
#   3. PULSAR START con el MANDO DEL JUGADOR 2.
#   4. Observar: ¿aparece Mickey? ¿el mando 2 lo mueve? ¿la cámara derecha lo sigue?
#   Reporta TODO lo que veas (el log dirá qué detecta el juego internamente).
# ============================================================================

PROC = "DisneyInfinity3.exe"
SPLIT_MODE = 2

session = frida.attach(PROC)

JS = r'''
var SPLIT_MODE = %d;
var base = Process.getModuleByName("DisneyInfinity3.exe").base;
var modsize = Process.getModuleByName("DisneyInfinity3.exe").size;
function A(rva){ return base.add(rva); }
function rvaOf(addr){ try{ var o=addr.sub(base); if(o.compare(ptr(modsize))<0 && o.compare(ptr(0))>=0) return "RVA "+o; }catch(e){} return addr.toString(); }

var RVA = { e01890:0xA01890, a9fd00:0x69FD00, de9dc0:0x9E9DC0, ce7e70:0x8E7E70,
            df3410:0x9F3410, addplayer:0x9D0D20, add10:0x14ADD10, camMgrGet:0x14ADCF0 };
var PTR_calcMode     = base.add(0x1C129F4);
var STUB             = base.add(0x569B60);
var DAT_splitMode    = base.add(0x01C117A8);
var DAT_numViewports = base.add(0x01C59D60);
var gCountPtr        = base.add(0x1E5F540);
var DAT_introFlag    = base.add(0x01E0191C);   // bypass candado 1-jugador (para el popup)
var DAT_camListHead  = base.add(0x1E8E8E4);
var P2_AVATAR = 0xf431d, POSX = 0x10000;

var mgr=null, frames=0, startPressed=false, startFrame=0, newHandle=0, joinArmed=false;
var patchDone=false, camDone=false, matMsg=false, frozenMsg=false;
var cam0Addr=null, cam1Addr=null, add10Log=0, camMsg=false, crashed=false;

var calcModeCb = new NativeCallback(function(){ return SPLIT_MODE; }, 'int', []);

Process.setExceptionHandler(function(det){
  if(crashed) return false; crashed=true;
  try{ send("!!!!! CRASH pc="+rvaOf(det.address)+" type="+det.type);
       if(det.memory) send("      acceso "+det.memory.operation+" @ "+det.memory.address); }catch(e){}
  return false;
});

function camsArray(){ var out=[], c=DAT_camListHead.readPointer(), i=0; while(!c.isNull() && i<8){ out.push(c); c=c.add(0x1c0).readPointer(); i++; } return out; }

// --- DETECTAR el Start del jugador 2 (FUN_00df3410 = evento figura/tag, se dispara al pulsar Start) ---
Interceptor.attach(A(RVA.df3410), {
  onEnter:function(){ if(!startPressed){ startPressed=true; startFrame=frames; send(">>> *** START DETECTADO (FUN_00df3410) — el jugador 2 pulsó Start. Empieza el cableado natural. ***"); } }
});
Interceptor.attach(A(RVA.addplayer), {
  onEnter:function(a){ send(">>> FUN_00dd0d20 (añadir jugador) llamado, slot="+a[0]); }
});

// --- capturar el handle del avatar cuando se cree (natural o asistido) ---
Interceptor.attach(A(RVA.a9fd00), {
  onEnter:function(a){ try{ var nh=a[2].toUInt32(); if(a[0].toInt32()===1 && nh!==0){ newHandle=nh;
     var g=gCountPtr.readPointer(); g.add(0x108).readPointer().add(0x50).add(0x48).writeU32(nh); } }catch(e){} }
});

// --- forzar el gate de update de cam1 (para que su update corra) ---
Interceptor.attach(A(RVA.add10), {
  onEnter:function(){ if(cam1Addr===null) return; var c=this.context.ecx;
    if(c.equals(cam1Addr)){ try{ var b0=c.add(0xB0).readU32(); if((b0&0xff)===0) c.add(0xB0).writeU32(b0|1); }catch(e){} } }
});

function repointCalc(){
  try{ Memory.protect(PTR_calcMode, Process.pointerSize, 'rw-'); }catch(e){}
  PTR_calcMode.writePointer(calcModeCb);
  send(">>> split activado (PTR_calcMode -> modo "+SPLIT_MODE+").");
}

Interceptor.attach(A(RVA.e01890), {
  onEnter:function(){
    if(mgr===null){ mgr=this.context.ecx; send("mgr="+mgr); }
    try{ DAT_introFlag.writeU32(1); }catch(e){}   // bypass candado 1-jugador (necesario para el popup)
    frames++;
    if(frames < 60) return;
    try{
      var g=gCountPtr.readPointer();
      var pA=mgr.add(0xC).readPointer(), pB=mgr.add(0x8).readPointer();

      if(!startPressed){
        // FASE POPUP: ARMAR la solicitud UNA SOLA VEZ (ponerla cada frame la auto-procesa
        // al instante sin popup). Set once -> el juego muestra "pulsa Start" y ESPERA.
        if(!joinArmed && frames > 120){
          joinArmed = true;
          pA.add(0x10).writeU32(P2_AVATAR); pA.add(0x58).writeU32(P2_AVATAR); pA.add(0x5C).writeU32(0);
          pB.add(0x10).writeU32(0);
          mgr.add(0x83a).writeU8(1);   // UNA VEZ -> dispara el popup y espera Start real
          send(">>> Solicitud ARMADA (una vez). DEBE SALIR EL POPUP. >>> PULSA START CON EL MANDO 2 <<<");
        }
        return;   // solo mantenemos DAT_introFlag=1 (arriba) cada frame; esperamos tu Start
      }

      // ---- FASE POST-START: el mando ya debería estar asignándose de forma natural ----
      // Completar el avatar (PC no tiene figura física; asistimos el spawn) hasta tener handle.
      if(g.add(0x94).readU32()<2) g.add(0x94).writeU32(2);
      if(newHandle === 0){
        pA.add(0x10).writeU32(P2_AVATAR); pA.add(0x58).writeU32(POSX); pA.add(0x5C).writeU32(0);
        pB.add(0x10).writeU32(0); pB.add(0x58).writeU32(0); pB.add(0x5C).writeU32(0);
        mgr.add(0x845).writeU8(0); mgr.add(0x880).writeU8(0); mgr.add(0x88c).writeU8(0);
        mgr.add(0x84b).writeU8(0); mgr.add(0x84c).writeU8(0);
        mgr.add(0x867).writeU8(1);
        if(mgr.add(0xcc).readS32() === -1){
          var ctxArr = g.add(0x108).readPointer(); var ctx1 = ctxArr.add(0x50);
          ctx1.add(0x10).writeU32(1); ctx1.add(0x48).writeU32(0x1);
          try{ ctx1.add(0x20).writeU8(ctxArr.add(0x20).readU8()); }catch(e){}
          mgr.add(0xcc).writeU32(1);
          if(!matMsg){ matMsg=true; send(">>> asistiendo el spawn del avatar del jugador 2..."); }
        }
      } else {
        // Mickey existe -> SOLIDIFICAR sin re-crear
        mgr.add(0x845).writeU8(1);
        if(!frozenMsg){ frozenMsg=true; send(">>> Mickey materializado (handle 0x"+newHandle.toString(16)+") y solidificado."); }
      }

      // split una vez existe el jugador 2
      if(!patchDone && newHandle!==0 && frames > startFrame+80){
        patchDone=true; repointCalc();
      }
      // identificar camaras + arreglos de camara
      if(patchDone && !camDone && frames > startFrame+120){
        camDone=true;
        var cams=camsArray();
        if(cams.length>=2){ cam0Addr=cams[0]; cam1Addr=cams[1];
          send(">>> "+cams.length+" camaras. Aplicando arreglos de camara al jugador 2."); }
      }
      if(camDone && cam1Addr){
        cam1Addr.add(0x1b4).writeU8(1); cam1Addr.add(0x158).writeU32(newHandle); cam1Addr.add(0x15c).writeU32(newHandle);
      }
    }catch(e){}
  }
});

// poll del estado de mando/jugador (para ver si el Start asigna el mando de forma natural)
var n=0;
setInterval(function(){
  if(mgr===null) return; n++;
  try{
    var g=gCountPtr.readPointer();
    send("   t"+n+": start="+startPressed+" count="+g.add(0x94).readU32()
      +" 0x83a="+mgr.add(0x83a).readU8()+" actorId1(0xcc)="+mgr.add(0xcc).readS32()
      +" ctrlIdx0(mgr+0x60)="+mgr.add(0x60).readS32()+" ctrlIdx1(mgr+0x64)="+mgr.add(0x64).readS32()
      +" newHandle=0x"+newHandle.toString(16)+" split="+DAT_splitMode.readU32()+" numVP="+DAT_numViewports.readU32());
  }catch(e){}
}, 1500);

send("join_and_split instalado. En ~2s sale el POPUP: PULSA START con el MANDO 2. Estate en la Toy Box.");
''' % SPLIT_MODE

def on_msg(m,d):
    print(m['payload'] if m['type']=='send' else m, flush=True)

s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(1)
except KeyboardInterrupt: pass
