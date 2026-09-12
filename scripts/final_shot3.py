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
var RVA = { e01890:0xA01890, dd19e0:0x9D19E0, de9dc0:0x9E9DC0, a9f080:0x69F080, aa36f0:0x6A36F0, a9fd00:0x69FD00 };

var gCountPtr = base.add(0x1E5F540);
var DAT_introFlag = base.add(0x01E0191C);
var P2_AVATAR = 0xf431d;
var POSX = 0x10000;
var mgr=null, frames=0, setupDone=false, newHandle=0;

Process.setExceptionHandler(function(det){
  try{
    send("########## EXCEPCION "+rvaOf(det.address)+" type="+det.type);
    var bt=Thread.backtrace(det.context,Backtracer.ACCURATE);
    var lines=["   BT:"]; for(var i=0;i<bt.length&&i<12;i++){ lines.push("     ["+i+"] "+rvaOf(bt[i])); }
    send(lines.join("\n"));
  }catch(e){}
  return false;
});

Interceptor.attach(A(RVA.dd19e0), { onEnter:function(a){ send(">> dd19e0 slot="+a[0]); } });
Interceptor.attach(A(RVA.de9dc0), { onEnter:function(){ send(">>>>>> de9dc0 MATERIALIZA"); } });
Interceptor.attach(A(RVA.a9f080), { onEnter:function(){ send(">>>>>> a9f080 POSICIONA JUGADOR 2"); } });
Interceptor.attach(A(RVA.aa36f0), { onEnter:function(a){ send("   aa36f0 cho="+a[0]); } });
// capturar el handle REAL del avatar del jugador 2 y ponerlo en ctx1+0x48
Interceptor.attach(A(RVA.a9fd00), {
  onEnter:function(a){
    send("   a9fd00 id="+a[0]+" old="+a[1]+" new="+a[2]);
    try{
      var nh = a[2].toUInt32();
      if(a[0].toInt32()===1 && nh!==0){
        newHandle = nh;
        var g=gCountPtr.readPointer(); var ctxArr=g.add(0x108).readPointer();
        ctxArr.add(0x50).add(0x48).writeU32(nh);  // ctx1+0x48 = handle real (corrige el temporal)
        send("   >>> ctx1+0x48 actualizado al handle REAL 0x"+nh.toString(16));
      }
    }catch(e){ send("   err handle: "+e); }
  }
});

Interceptor.attach(A(RVA.e01890), {
  onEnter:function(){
    if(mgr===null){ mgr=this.context.ecx; send("mgr="+mgr); }
    try{ DAT_introFlag.writeU32(1); }catch(e){}
    frames++;
    if(frames < 90) return;
    try{
      var pA=mgr.add(0xC).readPointer(), pB=mgr.add(0x8).readPointer();
      pA.add(0x10).writeU32(P2_AVATAR); pA.add(0x58).writeU32(POSX); pA.add(0x5C).writeU32(0);
      pB.add(0x10).writeU32(0); pB.add(0x58).writeU32(0); pB.add(0x5C).writeU32(0);
      mgr.add(0x845).writeU8(0); mgr.add(0x880).writeU8(0); mgr.add(0x88c).writeU8(0);
      mgr.add(0x84b).writeU8(0); mgr.add(0x84c).writeU8(0);
      mgr.add(0x867).writeU8(1);
      mgr.add(0x83a).writeU8(1);
      var g=gCountPtr.readPointer(); if(g.add(0x94).readU32()<2) g.add(0x94).writeU32(2);
      if(mgr.add(0xcc).readS32() === -1){
        var ctxArr = g.add(0x108).readPointer();
        var ctx1 = ctxArr.add(0x50);
        // SOLO escalares, NADA de copiar contenedores (evita corromper el heap):
        ctx1.add(0x10).writeU32(1);         // jugador local activo
        ctx1.add(0x48).writeU32(0x1);       // handle TEMPORAL no-cero (para pasar state 2; se corrige en a9fd00)
        // copiar SOLO el byte de direccion de split (+0x20), es escalar
        try{ ctx1.add(0x20).writeU8(ctxArr.add(0x20).readU8()); }catch(e){}
        mgr.add(0xcc).writeU32(1);
        send(">>> setup SELECTIVO (solo escalares ctx1+0x10=1, +0x48=temp, +0x20=dir). SIN copiar contenedores.");
      }
      if(!setupDone){ setupDone=true; send(">>> setup completo (frame "+frames+"). Observando..."); }
    }catch(e){ if(!setupDone) send("err: "+e); }
  }
});

setInterval(function(){
  if(mgr){ try{
    var g=gCountPtr.readPointer(); var ctxArr=g.add(0x108).readPointer();
    send("POLL count="+g.add(0x94).readU32()+" idx1="+mgr.add(0x64).readS32()+" state1(0x900)="+mgr.add(0x900).readS32()
      +" ctx1+0x10="+ctxArr.add(0x50).add(0x10).readU32()+" ctx1+0x48=0x"+ctxArr.add(0x50).add(0x48).readU32().toString(16));
  }catch(e){} }
}, 1500);

send("final_shot3 instalado (contexto SELECTIVO, sin copia). Estate quieto en el Toy Box.");
'''

def on_msg(m,d):
    print(m['payload'] if m['type']=='send' else m, flush=True)

s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(1)
except KeyboardInterrupt: pass
