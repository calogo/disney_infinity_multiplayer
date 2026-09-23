import frida, time

# Dispara una SECUENCIA de eventos nativos via el dispatcher (RVA 0x28bbb0).
# Convencion: thiscall(ecx=manager), [esp+4]=nombre, [esp+8]=arg1, [esp+c]=arg2.
# Ultima prueba de la via A: activar drop-in y luego "pulsar Start" para P2.

PROC = "DisneyInfinity3.exe"
# (nombre, arg1) en orden:
SEQ = [
  ("EnableDropIn", 1),
  ("EnableDropIn", 0),
  ("StartButtonPushed", 1),
]

print("Esperando el juego...", flush=True)
while True:
    try: session = frida.attach(PROC); break
    except frida.ProcessNotFoundError: time.sleep(0.2)
print("Enganchado.", flush=True)

import json
JS = r'''
var SEQ = %s;
var m = Process.getModuleByName("DisneyInfinity3.exe");
var base=m.base, sz=m.size;
function rvaOf(p){ try{ var o=p.sub(base); if(o.compare(ptr(sz))<0 && o.compare(ptr(0))>=0) return "RVA 0x"+o.toString(16);}catch(e){} return ""+p; }
function tryStr(p){ try{ if(p.isNull()) return null; var s=p.readCString(); if(s&&s.length>1&&s.length<40&&/^[\x20-\x7E]+$/.test(s)) return s;}catch(e){} return null; }
var KEY=/StartButton|EnableReader|DisableReader|GatewayTag|PlayerDropout|MissingAvatar|EnableDropIn|AvatarUnavailable|RequireValidAvatar|CreationComplete|AvatarSpawn|PlaceAvatar|WaitToJoin|NewPlayer|Join|DropIn/i;

var dispatch = new NativeFunction(base.add(0x28bbb0), 'void', ['pointer','pointer','int','int'], 'thiscall');
var ptrs = SEQ.map(function(e){ return [Memory.allocUtf8String(e[0]), e[1], e[0]]; });
var manager=null, fired=false, inFire=false, cascade=0;

Process.setExceptionHandler(function(d){ try{ send("!!! CRASH "+rvaOf(d.address)+" "+d.type+(d.memory?(" "+d.memory.operation+" @ "+d.memory.address):"")); }catch(e){} return false; });

Interceptor.attach(base.add(0x28bbb0), {
  onEnter:function(){
    var c=this.context;
    if(manager===null){ manager=c.ecx; send("manager = "+manager); }
    var name=null; try{ name=tryStr(c.esp.add(4).readPointer()); }catch(e){}
    if(fired && name && KEY.test(name) && !inFire){ cascade++; if(cascade<50) send("   [cascada] "+name+"  arg=0x"+c.esp.add(8).readU32().toString(16)+"  desde "+rvaOf(this.returnAddress)); }
    if(!fired && !inFire && manager!==null && name==="DestroyTaggedMissions"){
      fired=true; inFire=true;
      for(var i=0;i<ptrs.length;i++){
        send(">>> DISPARANDO "+ptrs[i][2]+"("+ptrs[i][1]+")");
        try{ dispatch(manager, ptrs[i][0], ptrs[i][1], 0); }catch(e){ send("   ERROR: "+e); }
      }
      send(">>> secuencia disparada. MIRA LA PANTALLA.");
      inFire=false;
    }
  }
});
send("[ok] listo. Estate DENTRO de la Toy Box mirando la pantalla.");
''' % json.dumps(SEQ)

def on_msg(m,d): print(m['payload'] if m['type']=='send' else m, flush=True)
s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(0.5)
except KeyboardInterrupt: pass
