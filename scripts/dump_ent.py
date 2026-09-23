import frida, time
PROC = "DisneyInfinity3.exe"
session = frida.attach(PROC)
JS = r'''
var e = ptr("0x1f639fb4");   // entidad de Hulk (esta sesion)
function f(o){ try{ return e.add(o).readFloat().toFixed(2); }catch(ex){ return "?"; } }
for(var row=0x100; row<0x210; row+=0x10){
  var line="+0x"+row.toString(16)+": ";
  for(var c=0;c<0x10;c+=4){ line += f(row+c)+"  "; }
  send(line);
}
send("== fin volcado ==");
'''
def on_msg(m,d): print(m['payload'] if m['type']=='send' else m, flush=True)
s=session.create_script(JS); s.on('message',on_msg); s.load()
time.sleep(2)
