import frida, time

# ============================================================================
# TEST SIMPLE DE PANTALLA PARTIDA (diagnostico) — Sesion 8
# SOLO llama FUN_006663e0(modo, 1) para partir la pantalla, SIN materializar
# el jugador 2. Sirve para aislar si el sistema de split funciona por si solo:
#   - Si la pantalla se parte (2 vistas del jugador 1) -> el split FUNCIONA,
#     el problema restante es solo la camara del jugador 2.
#   - Si crashea -> el render necesita 2 camaras activas antes de partir.
# Pulsa Ctrl pon SPLIT_MODE = 1 (horizontal) o 2 (vertical).
# ============================================================================

PROC = "DisneyInfinity3.exe"
SPLIT_MODE = 2

session = frida.attach(PROC)

JS = r'''
var SPLIT_MODE = %d;
var base = Process.getModuleByName("DisneyInfinity3.exe").base;
var modsize = Process.getModuleByName("DisneyInfinity3.exe").size;
function A(rva){ return base.add(rva); }
function rvaOf(addr){
  try{ var o=addr.sub(base); if(o.compare(ptr(modsize))<0 && o.compare(ptr(0))>=0) return "RVA "+o; }catch(e){}
  return addr.toString();
}
var RVA = { e01890:0xA01890 };
RVA.apply666 = 0x006663e0 - 0x400000;
var DAT_splitMode = base.add(0x01C117A8);   // _DAT_020117a8
var DAT_numViewports = base.add(0x01C59D60); // DAT_02059d60

var applySplit = new NativeFunction(A(RVA.apply666), 'void', ['int','int']);
var frames=0, done=false;

Process.setExceptionHandler(function(det){
  try{ send("!!!!! CRASH "+rvaOf(det.address)+" type="+det.type); }catch(e){}
  return false;
});

var reapplied = 0;
Interceptor.attach(A(RVA.e01890), {
  onLeave:function(){   // onLeave: DESPUES de que el game loop (FUN_018b0c60) haya reseteado el modo
    frames++;
    if(frames === 120 && !done){
      done = true;
      send(">>> modo split antes = "+DAT_splitMode.readU32()+", numViewports = "+DAT_numViewports.readU32());
      send(">>> aplicando FUN_006663e0("+SPLIT_MODE+", 1) CADA FRAME (contrarresta el reset del game loop)...");
    }
    // RE-APLICAR cada frame para ganarle al reset del game loop
    if(done){
      try{
        applySplit(SPLIT_MODE, 1);
        reapplied++;
        if(reapplied<=3 || reapplied===150 || reapplied===600){
          send("   re-aplicado #"+reapplied+" modo="+DAT_splitMode.readU32()+" numViewports="+DAT_numViewports.readU32());
        }
      }catch(e){ if(reapplied<3) send(">>> err: "+e); }
    }
  }
});

send("split_test_simple instalado (modo "+SPLIT_MODE+", SIN jugador 2). Estate en el Toy Box; en ~2s parte la pantalla.");
''' % SPLIT_MODE

def on_msg(m,d):
    print(m['payload'] if m['type']=='send' else m, flush=True)

s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(1)
except KeyboardInterrupt: pass
