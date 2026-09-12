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
var RVA = {
  e01890:0xA01890, aa36f0:0x6A36F0, a9fd00:0x69FD00, ddae30:0x9DAE30
};
RVA.gate_13a40a0 = 0x013a40a0 - 0x400000;
RVA.addplayer    = 0x00dd0d20 - 0x400000;
RVA.df3410       = 0x00df3410 - 0x400000;
RVA.db1810       = 0x00db1810 - 0x400000;
RVA.joinsm       = 0x00df21e0 - 0x400000;

var gCountPtr = base.add(0x1E5F540);
var DAT_225f548 = base.add(0x1E5F548);
var DAT_thresh = base.add(0x0176CF0C);
var DAT_introFlag = base.add(0x01E0191C);
var P2_AVATAR = 0xf431d, P2_FIG = 0xf431d;
var mgr=null, done=false;

Process.setExceptionHandler(function(det){
  try{
    send("!!!!! CRASH addr="+det.address+" ("+rvaOf(det.address)+") type="+det.type);
    var c=det.context;
    send("      eax="+c.eax+" ebx="+c.ebx+" ecx="+c.ecx+" edx="+c.edx+" esi="+c.esi+" edi="+c.edi+" ebp="+c.ebp+" esp="+c.esp+" pc="+c.pc);
  }catch(e){ send("!!!!! CRASH (err: "+e+")"); }
  return false;
});

// hooks de observacion pura sobre los hitos ya mapeados (poco frecuentes, no dan spam)
Interceptor.attach(A(RVA.gate_13a40a0), {
  onEnter:function(args){ send("=== FUN_013a40a0 (gate split-screen) llamado, slot="+args[0]); },
  onLeave:function(retval){ send("    -> resultado gate: "+retval+(retval.toInt32()!==0?" (PERMITIDO)":" (BLOQUEADO)")); }
});
Interceptor.attach(A(RVA.addplayer), {
  onEnter:function(args){ send("=== FUN_00dd0d20 (anadir jugador) llamado, slot="+args[0]); }
});
Interceptor.attach(A(RVA.df3410), {
  onEnter:function(){ send("=== FUN_00df3410 (evento figura/tag) disparado - !inesperado, no lo llamamos nosotros!"); }
});
Interceptor.attach(A(RVA.aa36f0), {
  onEnter:function(args){ send("=== aa36f0 NATURAL disparado, cho="+args[0]); }
});
Interceptor.attach(A(RVA.a9fd00), {
  onEnter:function(args){ send("=== a9fd00 NATURAL disparado id="+args[0]+" old="+args[1]+" new="+args[2]); }
});
var db1810Count = 0;
Interceptor.attach(A(RVA.db1810), {
  onEnter:function(){ if(db1810Count<10){ send("&&& FUN_00db1810() ENTRA"); } },
  onLeave:function(retval){
    if(db1810Count<10){ db1810Count++; send("&&& FUN_00db1810() -> raw="+retval+" low-byte="+(retval.toInt32()&0xff)); }
  }
});
var joinsmCount = 0;
Interceptor.attach(A(RVA.joinsm), {
  onEnter:function(){ if(joinsmCount<3){ joinsmCount++; send("@@@ FUN_00df21e0 (join state machine, linea 194) SI se alcanza"); } }
});
var ddaeCount = 0;
Interceptor.attach(A(RVA.ddae30), {
  onEnter:function(args){
    this.slot = args[0].toInt32();
    this.sku = args[1];
    this.errOut = args[2];
  },
  onLeave:function(retval){
    if(this.slot===1 && ddaeCount<15){
      ddaeCount++;
      var err = -1;
      try{ if(!this.errOut.isNull()) err = this.errOut.readS32(); }catch(e){}
      send("### FUN_00ddae30(slot=1, sku="+this.sku+") -> "+retval+"  errOut="+err);
    }
  }
});

Interceptor.attach(A(RVA.e01890), {
  onEnter:function(){
    if(mgr===null){ mgr=this.context.ecx; send("mgr="+mgr); }
    // FORZAR CADA FRAME: algo resetea DAT_introFlag a 0 antes de que corra el resto de la logica
    if(done){
      try{ DAT_introFlag.writeU32(1); }catch(e){}
    }
    if(done) return;
    done=true;
    setTimeout(function(){
      try{
        var pA=mgr.add(0xC).readPointer(), pB=mgr.add(0x8).readPointer();
        pA.add(0x10).writeU32(P2_AVATAR);
        pA.add(0x58).writeU32(P2_FIG);
        pA.add(0x5C).writeU32(0);
        pB.add(0x10).writeU32(0);
        mgr.add(0x83a).writeU8(1);   // <<<< LA SOLICITUD DE UNION, disparador natural
        DAT_introFlag.writeU32(1);  // <<<< bypass del candado "iVar15==1 && DAT_0220191c==0"
        send(">>> DAT_introFlag releido inmediatamente tras escribir="+DAT_introFlag.readU32());
        send(">>> Escrito: pA+0x10(SKU)=0x"+P2_AVATAR.toString(16)+" pB+0x10=0 mgr+0x83a=1");
        send(">>> pA="+pA+" pB="+pB+" releido pA+0x10=0x"+pA.add(0x10).readU32().toString(16)+" pB+0x10=0x"+pB.add(0x10).readU32().toString(16)+" mgr+0x83a(releido)="+mgr.add(0x83a).readU8());
        send(">>> Contador de jugadores actual (sin forzar): "+gCountPtr.readPointer().add(0x94).readU32());
      }catch(e){ send("err escribiendo: "+e); }
    }, 1500);
  }
});

setInterval(function(){
  if(mgr){
    try{
      var g=gCountPtr.readPointer();
      var earlyExit = "?";
      try{ earlyExit = DAT_225f548.readPointer().add(0x89).readU8(); }catch(e){ earlyExit = "err:"+e; }
      send("POLL 0x83a="+mgr.add(0x83a).readU8()+" count="+g.add(0x94).readU32()
        +" idx0="+mgr.add(0x60).readS32()+" idx1="+mgr.add(0x64).readS32()
        +" mgr+0xa20="+mgr.add(0xa20).readFloat()
        +" mgr+0x841(quit)="+mgr.add(0x841).readU8()+" mgr+0x854="+mgr.add(0x854).readU8()
        +" EARLYEXIT(0225f548+0x89)="+earlyExit
        +" DAT_thresh="+DAT_thresh.readFloat()
        +" DAT_introFlag="+DAT_introFlag.readU32()
        +" g+0x9a="+g.add(0x9a).readU8()+" mgr+0xd3="+mgr.add(0xd3).readU8()+" mgr+0xb60="+mgr.add(0xb60).readU32()
        +" mgr+0xd4="+mgr.add(0xd4).readU8()+" mgr+0x78="+mgr.add(0x78).readS32()+" mgr+0x83c="+mgr.add(0x83c).readU8()
        +" mgr+0xb8c="+mgr.add(0xb8c).readU8()
        +" mgr+0xc(pA-actual)="+mgr.add(0xc).readPointer()+" mgr+0x8(pB-actual)="+mgr.add(0x8).readPointer()
        +" pA-actual+0x10=0x"+mgr.add(0xc).readPointer().add(0x10).readU32().toString(16)
        +" pB-actual+0x10=0x"+mgr.add(0x8).readPointer().add(0x10).readU32().toString(16)
        +" 0xcc(actorId1)=0x"+mgr.add(0xcc).readU32().toString(16));
    }catch(e){}
  }
}, 1000);

send("natural_join instalado. Estate ya dentro y estable en el Toy Box.");
'''

def on_msg(m,d):
    print(m['payload'] if m['type']=='send' else m, flush=True)

s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(1)
except KeyboardInterrupt: pass
