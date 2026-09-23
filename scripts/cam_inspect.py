import frida, time
PROC = "DisneyInfinity3.exe"
session = frida.attach(PROC)
JS = r'''
var base = Process.getModuleByName("DisneyInfinity3.exe").base;
var HEAD = base.add(0x1E8E8E4);   // cabeza lista camaras, next en +0x1c0
function fx(c,o){ try{ return c.add(o).readFloat().toFixed(1); }catch(e){ return "?"; } }
setInterval(function(){
  try{
    var c=HEAD.readPointer(), i=0, out=[];
    while(!c.isNull() && i<8){
      var line="cam#"+i+" @"+c;
      try{ line+=" act+0x2c="+c.add(0x2c).readU8(); }catch(e){}
      try{ line+=" follow+0x1b4="+c.add(0x1b4).readU8(); }catch(e){}
      try{ line+=" handle+0x158=0x"+c.add(0x158).readU32().toString(16); }catch(e){}
      // matriz de vista +0xc0.. (traslacion aprox) y target
      line+=" view+0xf0=["+fx(c,0xf0)+","+fx(c,0xf4)+","+fx(c,0xf8)+"]";
      out.push(line);
      c=c.add(0x1c0).readPointer(); i++;
    }
    send("=== "+out.length+" camaras ===\n"+out.join("\n"));
  }catch(e){ send("err "+e); }
}, 2000);
send("cam_inspect instalado.");
'''
def on_msg(m,d): print(m['payload'] if m['type']=='send' else m, flush=True)
s=session.create_script(JS); s.on('message',on_msg); s.load()
try:
    while True: time.sleep(0.5)
except KeyboardInterrupt: pass
