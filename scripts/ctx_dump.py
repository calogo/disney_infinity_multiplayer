import frida, time
PROC = "DisneyInfinity3.exe"
session = frida.attach(PROC)
JS = r'''
var base = Process.getModuleByName("DisneyInfinity3.exe").base;
var gamePlayers=null;
try{ gamePlayers=ptr(ptr(base.add(0x69E3CF+2).readU32()).readU32()); }catch(e){}
var dat=null; try{ dat=ptr(base.add(0x1E5F540).readU32()); }catch(e){}
send("gamePlayers="+gamePlayers+"  DAT_0225f540="+dat+(gamePlayers&&dat&&gamePlayers.equals(dat)?" (IGUALES)":" (distintos)"));

function dumpCtx(name, mgr){
  if(!mgr) return;
  try{
    var arr=mgr.add(0x108).readPointer();
    send("== "+name+" ctxArr="+arr+" ==");
    for(var slot=0;slot<2;slot++){
      var c=arr.add(slot*0x50);
      var line="  ctx["+slot+"] @"+c+": ";
      for(var o=0;o<0x50;o+=4){ line+="+"+o.toString(16)+"=0x"+c.add(o).readU32().toString(16)+" "; }
      send(line);
    }
  }catch(e){ send("  err "+e); }
}
dumpCtx("gamePlayers", gamePlayers);
if(dat && (!gamePlayers || !dat.equals(gamePlayers))) dumpCtx("DAT_0225f540", dat);
send("== fin ==");
'''
def on_msg(m,d): print(m['payload'] if m['type']=='send' else m, flush=True)
s=session.create_script(JS); s.on('message',on_msg); s.load()
time.sleep(2)
