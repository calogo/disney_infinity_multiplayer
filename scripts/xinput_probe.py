import frida, time

# FASE 1 del titere: confirmar que podemos LEER el mando 2 (XInput indice 1)
# desde nuestro inyector, y ver que mandos consulta el juego.
#  - Hook XInputGetState: loguea con que dwUserIndex llama el juego (que mandos ve).
#  - Nosotros llamamos XInputGetState(1) cada 300ms y logueamos stick/botones del mando 2.
# Si vemos moverse el stick del mando 2 en el log -> tenemos la fuente de input del titere.

PROC = "DisneyInfinity3.exe"
print("Esperando el juego...", flush=True)
while True:
    try: session = frida.attach(PROC); break
    except frida.ProcessNotFoundError: time.sleep(0.2)
print("Enganchado.", flush=True)

JS = r'''
function findExp(name){ var mods=Process.enumerateModules(); for(var i=0;i<mods.length;i++){ try{ var p=mods[i].findExportByName(name); if(p) return [p, mods[i].name]; }catch(e){} } return null; }

// localizar XInputGetState (varias dll posibles)
var xi = findExp("XInputGetState");
if(!xi){ send("XInputGetState NO encontrado aun; reintentando..."); }
function setup(){
  xi = findExp("XInputGetState");
  if(!xi){ setTimeout(setup, 300); return; }
  send("XInputGetState en "+xi[1]+" @ "+xi[0]);
  var seenIdx={};
  Interceptor.attach(xi[0], {
    onEnter:function(a){ var idx=a[0].toInt32(); if(!seenIdx[idx]){ seenIdx[idx]=1; send("[juego] consulta XInput indice "+idx); } }
  });
  // funcion para llamarla nosotros
  var XInputGetState = new NativeFunction(xi[0], 'uint32', ['uint32','pointer']);
  var buf = Memory.alloc(16);   // XINPUT_STATE: dwPacketNumber(4) + GAMEPAD(12): wButtons(2),LT(1),RT(1),LX(2),LY(2),RX(2),RY(2)
  var last="";
  setInterval(function(){
    try{
      var r = XInputGetState(1, buf);   // indice 1 = MANDO 2
      if(r!==0){ if(last!=="off"){ last="off"; send("[mando2] no conectado (idx1) ret="+r); } return; }
      var btn = buf.add(4).readU16();
      var lx = buf.add(10).readS16(), ly = buf.add(12).readS16();
      var rx = buf.add(14).readS16(), ry = buf.add(16-2).readS16();
      var s = "btn=0x"+btn.toString(16)+" LX="+lx+" LY="+ly;
      // solo loguear si hay actividad (stick fuera de zona muerta o boton)
      if(btn!==0 || Math.abs(lx)>8000 || Math.abs(ly)>8000){
        if(s!==last){ last=s; send("[mando2 ACTIVO] "+s); }
      }
    }catch(e){ send("err poll: "+e); }
  }, 250);
  send("[ok] leyendo mando 2 (XInput idx 1). MUEVE EL STICK del 2o mando o pulsa botones.");
}
setup();
'''
def on_msg(m,d): print(m['payload'] if m['type']=='send' else m, flush=True)
s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(0.5)
except KeyboardInterrupt: pass
