import frida, time

# Observa el DISPATCHER de eventos StartingZoneLauncher_inner (RVA 0x28bbb0).
# Loguea, para cada evento, los registros y pila candidatos a llevar el NOMBRE del
# evento y el indice de jugador. Filtra a eventos del JOIN para no spamear.
# Objetivo: ver la secuencia de eventos del join y capturar la convencion + el
# puntero del manager, para luego DISPARAR "StartButtonPushed"/"EnableReaderPlayer" para P2.

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
function tryStr(p){ try{ if(p.isNull()) return null; var s=p.readCString(); if(s && s.length>1 && s.length<40 && /^[\x20-\x7E]+$/.test(s)) return s; }catch(e){} return null; }
var KEY = /StartButton|EnableReader|DisableReader|GatewayTag|GatewayConnected|GatewayDisconnected|PlayerDropout|MissingAvatar|EnableDropIn|DisableDropIn|AvatarUnavailable|RequireValidAvatar|CreationComplete|AvatarSpawn|StartButtonPushed|SwitchProfile|PlaceAvatar|WaitToJoin|NewPlayer/i;
var nAll=0, lastName="";

Interceptor.attach(base.add(0x28bbb0), {
  onEnter:function(a){
    var c=this.context;
    // buscar el nombre del evento en registros y pila
    var cand = { ecx:tryStr(c.ecx), edx:tryStr(c.edx), esi:tryStr(c.esi), edi:tryStr(c.edi),
                 eax:tryStr(c.eax), s4:tryStr(c.esp.add(4).readPointer?c.esp.add(4).readPointer():ptr(0)) };
    var name=null, where="";
    for(var k in cand){ if(cand[k]){ name=cand[k]; where=k; break; } }
    // tambien probar [esp+4] y [esp+8] como punteros a string
    if(!name){ try{ var p1=c.esp.add(4).readPointer(); name=tryStr(p1); if(name) where="[esp+4]"; }catch(e){} }
    if(!name) return;
    if(!KEY.test(name)) return;   // solo eventos del join
    if(name===lastName) return;   // dedup consecutivo
    lastName=name;
    nAll++;
    if(nAll>80) return;
    var idx="?"; try{ idx="0x"+c.esp.add(8).readU32().toString(16); }catch(e){}
    send(">>> EVENTO JOIN \""+name+"\"  manager(ecx)="+c.ecx+"  arg1(idx)="+idx+"  <- desde "+rvaOf(this.returnAddress));
  }
});
send("[ok] observador de eventos puesto (RVA 0x28bbb0). Haz cosas: entra/sal de toybox, cambia personaje, PULSA START en el 2o mando. Mira que eventos del join disparan.");
'''
def on_msg(m,d): print(m['payload'] if m['type']=='send' else m, flush=True)
s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(0.5)
except KeyboardInterrupt: pass
