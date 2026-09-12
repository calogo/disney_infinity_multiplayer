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
var RVA = { e01890:0xA01890, dd19e0:0x9D19E0, de9dc0:0x9E9DC0, a9fd00:0x69FD00 };
var gCountPtr = base.add(0x1E5F540);
var DAT_introFlag = base.add(0x01E0191C);
var DAT_camListAddr = base.add(0x1E8E8E4);  // Ghidra 0x0228e8e4 - 0x400000
var P2_AVATAR = 0xf431d, POSX = 0x10000;
var mgr=null, frames=0, dumped=false, newHandle=0, assigned=false;

Process.setExceptionHandler(function(det){
  try{ send("!!!!! CRASH "+rvaOf(det.address)+" type="+det.type); }catch(e){}
  return false;
});

Interceptor.attach(A(RVA.a9fd00), {
  onEnter:function(a){
    try{ var nh=a[2].toUInt32(); if(a[0].toInt32()===1 && nh!==0){
      newHandle = nh;
      var g=gCountPtr.readPointer(); g.add(0x108).readPointer().add(0x50).add(0x48).writeU32(nh);
    }}catch(e){}
  }
});

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
        send(">>> jugador 2 activado.");
      }
      // ASIGNAR el avatar del jugador 2 a la camara 2 (+0x158/+0x15c)
      if(!assigned && frames > 150 && newHandle !== 0){
        assigned = true;
        try{
          var camHead = DAT_camListAddr.readPointer();
          var cams = [];
          var n=0, cam=camHead;
          while(!cam.isNull() && n<4){ cams.push(cam); cam = cam.add(0x1c0).readPointer(); n++; }
          send(">>> total camaras = "+cams.length+", handle jugador 2 = 0x"+newHandle.toString(16));
          if(cams.length >= 2){
            var c1 = cams[1];
            send(">>> cam1 antes: +0x158=0x"+c1.add(0x158).readU32().toString(16)+" +0x15c=0x"+c1.add(0x15c).readU32().toString(16));
            c1.add(0x158).writeU32(newHandle);
            c1.add(0x15c).writeU32(newHandle);
            send(">>> ASIGNADO avatar jugador2 (0x"+newHandle.toString(16)+") a cam1+0x158/+0x15c. MIRA LA PANTALLA.");
          }
        }catch(e){ send("err asignando camara: "+e); }
      }
    }catch(e){}
  }
});

send("dump_viewport instalado. Materializa jugador 2 y vuelca el objeto de viewport. Estate quieto en el Toy Box.");
'''

def on_msg(m,d):
    print(m['payload'] if m['type']=='send' else m, flush=True)

s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(1)
except KeyboardInterrupt: pass
