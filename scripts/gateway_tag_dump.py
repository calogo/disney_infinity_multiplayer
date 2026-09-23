import frida, time

# Vuelca la ESTRUCTURA del "tag" (figura) que viaja en el evento GatewayTagChange.
# Dispatcher StartingZoneLauncher_inner (RVA 0x28bbb0): ecx=manager, [esp+4]=nombre, [esp+8]=arg.
# Para GatewayTagChange, [esp+8] = puntero a la estructura de la figura.
# Objetivo: ver el indice de jugador y el SKU dentro del tag, para poder fabricar
# uno de P2 (jugador 1) y disparar GatewayTagChange nosotros = "P2 puso figura".

PROC = "DisneyInfinity3.exe"
print("Esperando el juego...", flush=True)
while True:
    try: session = frida.attach(PROC); break
    except frida.ProcessNotFoundError: time.sleep(0.2)
print("Enganchado.", flush=True)

JS = r'''
var m = Process.getModuleByName("DisneyInfinity3.exe");
var base=m.base, sz=m.size;
function rvaOf(p){ try{ var o=p.sub(base); if(o.compare(ptr(sz))<0 && o.compare(ptr(0))>=0) return "RVA 0x"+o.toString(16);}catch(e){} return ""+p; }
function tryStr(p){ try{ if(p.isNull()) return null; var s=p.readCString(); if(s&&s.length>1&&s.length<40&&/^[\x20-\x7E]+$/.test(s)) return s;}catch(e){} return null; }

Interceptor.attach(base.add(0x28bbb0), {
  onEnter:function(){
    var c=this.context;
    var name=null; try{ name=tryStr(c.esp.add(4).readPointer()); }catch(e){}
    if(name!=="GatewayTagChange" && name!=="GatewayAddTag") return;
    var tag; try{ tag=c.esp.add(8).readPointer(); }catch(e){ return; }
    send("=== "+name+"  manager="+c.ecx+"  tag="+tag+"  desde "+rvaOf(this.returnAddress)+" ===");
    try{ send(hexdump(tag,{length:0x60,header:true,ansi:false})); }catch(e){ send("no hexdump: "+e); }
    // buscar candidatos: SKUs (0xf4xxx) e indices pequenos (0/1)
    try{
      var s="  dwords: ";
      for(var i=0;i<0x18;i++){ var v=tag.add(i*4).readU32()>>>0; s+="+"+(i*4).toString(16)+"=0x"+v.toString(16)+" "; }
      send(s);
    }catch(e){}
  }
});
send("[ok] volcado de tag puesto. CAMBIA de personaje (Mi coleccion) para capturar la estructura del tag.");
'''
def on_msg(m,d): print(m['payload'] if m['type']=='send' else m, flush=True)
s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(0.5)
except KeyboardInterrupt: pass
