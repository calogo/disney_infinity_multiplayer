import frida, time
PROC = "DisneyInfinity3.exe"
session = frida.attach(PROC)
JS = r'''
var base = Process.getModuleByName("DisneyInfinity3.exe").base;
var obj = ptr(base.add(0x1D40194).readU32());   // DAT_02140194 (gestor de mandos)
send("obj(gestor mandos)="+obj);
function locked(pi){ return obj.add(0x44c + pi*4).readS32(); }
send("ANTES: P0="+locked(0)+" P1="+locked(1)+" P2="+locked(2)+" P3="+locked(3)+" count="+obj.add(0x478).readU32());

// atar el mando 1 (2o controlador) al jugador indice 1 (Mickey/P2)
if(locked(1) === -1 || locked(1) !== 1){
  obj.add(0x44c + 1*4).writeS32(1);          // [obj+0x450] = 1
  obj.add(0x478).add(0).writeU32(obj.add(0x478).readU32()+1);
  // notificar al sistema de input
  try{ var notify=new NativeFunction(base.add(0x410e0), 'void', ['pointer'], 'thiscall'); notify(obj); send("notify 0x410e0 OK"); }catch(e){ send("notify err (no critico): "+e); }
  send(">>> mando 1 atado al jugador 1 (Mickey). MUEVE EL MANDO 2.");
}
send("DESPUES: P0="+locked(0)+" P1="+locked(1)+" P2="+locked(2)+" count="+obj.add(0x478).readU32());
'''
def on_msg(m,d): print(m['payload'] if m['type']=='send' else m, flush=True)
s=session.create_script(JS); s.on('message',on_msg); s.load()
time.sleep(2)
