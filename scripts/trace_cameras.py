import frida, time

PROC = "DisneyInfinity3.exe"
session = frida.attach(PROC)

JS = r'''
var base = Process.getModuleByName("DisneyInfinity3.exe").base;
var modsize = Process.getModuleByName("DisneyInfinity3.exe").size;
function A(rva){ return base.add(rva); }
function rvaOf(addr){
  try{ var o=addr.sub(base); if(o.compare(ptr(modsize))<0 && o.compare(ptr(0))>=0) return "RVA "+o; }catch(e){}
  return addr.toString();
}
// Ghidra addr - 0x400000 = RVA
var RVA = { e01890:0xA01890, dd19e0:0x9D19E0, de9dc0:0x9E9DC0 };
RVA.a3d00   = 0x013a3d00 - 0x400000;  // asigna camaras
RVA.a3f90   = 0x013a3f90 - 0x400000;  // aplica direccion de split por jugador
RVA.ac8f0   = 0x013ac8f0 - 0x400000;  // callback aplicar split
RVA.kick    = 0x00cfde50 - 0x400000;  // SplitScreenKick (recarga viewport)
RVA.a3f78   = 0x013773c0 - 0x400000;  // setter flag direccion split

var gCountPtr = base.add(0x1E5F540);
var DAT_introFlag = base.add(0x01E0191C);
var P2_AVATAR = 0xf431d, POSX = 0x10000;
var mgr=null, frames=0, phase=0;

function trace(name, rva){
  Interceptor.attach(A(rva), {
    onEnter:function(a){ send("### CAMARA/SPLIT: "+name+" LLAMADO (arg0="+a[0]+")"); }
  });
}
trace("a3d00 (asigna camaras)", RVA.a3d00);
trace("a3f90 (aplica split x jugador)", RVA.a3f90);
trace("ac8f0 (callback split)", RVA.ac8f0);
trace("SplitScreenKick (viewport)", RVA.kick);
trace("013773c0 (flag direccion split)", RVA.a3f78);
Interceptor.attach(A(RVA.de9dc0), { onEnter:function(){ send(">>>>>> de9dc0 MATERIALIZA jugador 2"); } });

Interceptor.attach(A(RVA.e01890), {
  onEnter:function(){
    if(mgr===null){ mgr=this.context.ecx; send("mgr="+mgr); }
    try{ DAT_introFlag.writeU32(1); }catch(e){}
    frames++;
    if(frames < 90) return;
    try{
      var g=gCountPtr.readPointer();
      var pA=mgr.add(0xC).readPointer(), pB=mgr.add(0x8).readPointer();
      pA.add(0x10).writeU32(P2_AVATAR); pA.add(0x58).writeU32(POSX); pA.add(0x5C).writeU32(0);
      pB.add(0x10).writeU32(0); pB.add(0x58).writeU32(0); pB.add(0x5C).writeU32(0);
      mgr.add(0x845).writeU8(0); mgr.add(0x880).writeU8(0); mgr.add(0x88c).writeU8(0);
      mgr.add(0x84b).writeU8(0); mgr.add(0x84c).writeU8(0);
      mgr.add(0x867).writeU8(1); mgr.add(0x83a).writeU8(1);
      if(g.add(0x94).readU32()<2) g.add(0x94).writeU32(2);
      if(mgr.add(0xcc).readS32() === -1){
        var ctxArr = g.add(0x108).readPointer(); var ctx1 = ctxArr.add(0x50);
        ctx1.add(0x10).writeU32(1); ctx1.add(0x48).writeU32(0x1);
        try{ ctx1.add(0x20).writeU8(ctxArr.add(0x20).readU8()); }catch(e){}
        mgr.add(0xcc).writeU32(1);
        send(">>> jugador 2 activado (ctx1+0x10=1). Observando si se dispara ALGUNA funcion de camara/split...");
      }
    }catch(e){}
  }
});

send("trace_cameras instalado. Observa QUE funciones de camara se disparan al aparecer el jugador 2.");
'''

def on_msg(m,d):
    print(m['payload'] if m['type']=='send' else m, flush=True)

s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(1)
except KeyboardInterrupt: pass
