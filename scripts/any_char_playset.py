import frida, time

# ============================================================================
# CUALQUIER PERSONAJE EN CUALQUIER PLAY SET  (Sesión 10 - objetivo alternativo)
# ----------------------------------------------------------------------------
# FUN_00ddae30(this, slot, sku, &errCode, p5, p6) = validación real de compatibilidad
# personaje<->playset. Devuelve 1=compatible, 0=NO compatible (y pone *errCode:
#   1=MissingPlayset, 2=CrossOverNotAllowed, 3=CrossOverLocked, 4,6,7=SKUOnly, 8,9...).
# Forzamos: si el resultado natural es 0 (bloqueado), lo cambiamos a 1 y errCode=0.
# -> el juego deja entrar a cualquier personaje en cualquier Play Set.
# ----------------------------------------------------------------------------
# CÓMO PROBAR: con esto corriendo, coge un personaje que normalmente NO se permite
# en un Play Set (p.ej. un personaje de Marvel para el Play Set de Star Wars) e intenta
# ENTRAR a ese Play Set. Debería dejarte pasar sin el aviso de "no permitido".
# ============================================================================

PROC = "DisneyInfinity3.exe"
session = frida.attach(PROC)

JS = r'''
var base = Process.getModuleByName("DisneyInfinity3.exe").base;
function A(rva){ return base.add(rva); }
var ddae30 = A(0x9DAE30);   // FUN_00ddae30 (0x00ddae30 - 0x400000)

var forced=0, allowed=0, calls=0;
Interceptor.attach(ddae30, {
  onEnter:function(args){
    // args[0]=slot, args[1]=sku, args[2]=&errCode  (this va en ecx, no en args)
    this.sku = args[1];
    this.errOut = args[2];
    calls++;
  },
  onLeave:function(retval){
    if(retval.toInt32() === 0){          // el juego lo bloquearía
      try{ if(!this.errOut.isNull()) this.errOut.writeS32(0); }catch(e){}   // errCode = OK
      retval.replace(1);                 // -> compatible
      forced++;
      if(forced<=25) send(">>> BLOQUEO ANULADO (sku=0x"+this.sku.toString(16)+") -> personaje permitido.");
    } else {
      allowed++;
    }
  }
});

setInterval(function(){
  send("   estado: llamadas="+calls+" ya-permitidos="+allowed+" bloqueos-anulados="+forced);
}, 3000);

send("any_char_playset instalado. Coge un personaje 'no permitido' e intenta ENTRAR a ese Play Set. Debería dejarte.");
'''

def on_msg(m,d):
    print(m['payload'] if m['type']=='send' else m, flush=True)

s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(1)
except KeyboardInterrupt: pass
