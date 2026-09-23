import frida, time

# ============================================================================
# PROTOTIPO "BASE VIRTUAL con 2 FIGURAS" (idea del usuario, dia nuevo sesion 12)
# Registra al Jugador 2 en la CARGA de la Toy Box (via correcta del HANDOFF):
#   - mgr+0xb8c = 1          -> el bucle de creacion recorre 2 slots
#   - playerCount = 2        -> [DAT_0225f540]+0x94
#   - DAT_0220191c = 1       -> desbloquea e01890 para 2 jugadores (candado 1-player)
#   - pA+0x10 = P2_SKU       -> avatar solicitado slot 1
#   - pA+0x58 = P2_SKU       -> figID.lo slot1 (la "figura" puesta)
#   - pB+0x10 = 0            -> "anterior" vacio => hay cambio real (dispara join)
# FASE 2 (cuando el handle de P2 = mgr+0x64 es valido): dejar de re-disparar para
#   que se asiente (sin skip-slot, para no matar el mando). Solo observar.
# USO: lanzar en el MENU. P1: elige TU personaje. Entrar a una Toy Box VACIA.
#      Prueba el MANDO 2 cuando aparezca el 2o personaje.
# ============================================================================

PROC = "DisneyInfinity3.exe"
P2_SKU = 0xf431d   # figura del Jugador 2 (elige OTRO personaje como P1 para distinguirlos)

print("Esperando el juego (lanzalo desde Steam)...", flush=True)
while True:
    try: session = frida.attach(PROC); break
    except frida.ProcessNotFoundError: time.sleep(0.2)
print("Enganchado.", flush=True)

JS = r'''
var P2_SKU = %d;
var m = Process.getModuleByName("DisneyInfinity3.exe");
var base = m.base, modsize = m.size;
function A(rva){ return base.add(rva); }
function rvaOf(p){ try{ var o=p.sub(base); if(o.compare(ptr(modsize))<0 && o.compare(ptr(0))>=0) return "RVA 0x"+o.toString(16);}catch(e){} return ""+p; }
function u(p,off){ try{ return "0x"+p.add(off).readU32().toString(16);}catch(e){ return "?"; } }

var e01890   = A(0xA01890);
var gCountPtr= A(0x1E5F540);   // DAT_0225f540 (puntero al gestor de jugadores)
var unlock   = A(0x1E0191C);   // DAT_0220191c (candado 1-player en e01890)

var mgr=null, frames=0, phase=1, p2handle=0, crashed=false;

Process.setExceptionHandler(function(d){
  if(crashed) return false; crashed=true;
  try{ send("!!! CRASH "+rvaOf(d.address)+" "+d.type+(d.memory?(" "+d.memory.operation+" @ "+d.memory.address):"")); }catch(e){}
  return false;
});

Interceptor.attach(e01890, {
  onEnter:function(){
    if(mgr===null){ mgr=this.context.ecx; send("mgr = "+mgr+"  (base virtual activa; registrando P2 en la carga)"); }
    frames++;
    try{
      // estructural (siempre): 2 slots, 2 jugadores, candado abierto
      mgr.add(0xb8c).writeU8(1);
      try{ var g=gCountPtr.readPointer(); if(!g.isNull() && g.add(0x94).readU32()<2) g.add(0x94).writeU32(2); }catch(e){}
      unlock.writeU32(1);

      var pA = mgr.add(0xc).readPointer();
      var pB = mgr.add(0x8).readPointer();
      var h = mgr.add(0x64).readU32();   // handle jugador 2

      if(phase===1){
        // disparar la "figura puesta" en slot 1
        if(!pA.isNull()){ pA.add(0x10).writeU32(P2_SKU); pA.add(0x58).writeU32(P2_SKU); pA.add(0x5c).writeU32(0); }
        if(!pB.isNull()){ pB.add(0x10).writeU32(0); }
        try{ mgr.add(0xa20).writeFloat(0.0); }catch(e){}   // timer expirado
        if(h!==0 && h!==0xffffffff){
          phase=2; p2handle=h;
          send(">>> JUGADOR 2 MATERIALIZADO! handle=0x"+h.toString(16)+"  -> fase 2 (asentar, deja de re-disparar). PRUEBA EL MANDO 2.");
        }
      }
      // fase 2: no re-disparamos (dejamos que se asiente). Solo mantenemos lo estructural de arriba.
    }catch(e){}
  }
});

var n=0;
setInterval(function(){
  if(mgr===null) return; n++;
  try{
    var g=gCountPtr.readPointer();
    var pA=mgr.add(0xc).readPointer();
    send("  t"+n+" fase"+phase+": players="+(g.isNull()?"?":u(g,0x94))+
         " b8c="+u(mgr,0xb8c)+" sku1="+(pA.isNull()?"?":u(pA,0x10))+
         " | P1(0x60)="+u(mgr,0x60)+" P2(0x64)="+u(mgr,0x64));
  }catch(e){}
}, 2000);

send("base_2figuras instalado. Estas en el MENU: elige tu personaje (P1) y ENTRA a una Toy Box VACIA. Mira si sale un 2o personaje y prueba el mando 2.");
''' % P2_SKU

def on_msg(m,d):
    print(m['payload'] if m['type']=='send' else m, flush=True)

s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(1)
except KeyboardInterrupt: pass
