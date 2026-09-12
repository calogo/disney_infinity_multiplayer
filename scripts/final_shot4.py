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
var mgr=null, frames=0, phase=0, matCount=0;

Process.setExceptionHandler(function(det){
  try{
    send("########## EXCEPCION "+rvaOf(det.address)+" type="+det.type);
    var bt=Thread.backtrace(det.context,Backtracer.ACCURATE);
    var lines=["   BT:"]; for(var i=0;i<bt.length&&i<12;i++){ lines.push("     ["+i+"] "+rvaOf(bt[i])); }
    send(lines.join("\n"));
  }catch(e){}
  return false;
});

Interceptor.attach(A(RVA.de9dc0), { onEnter:function(){ matCount++; if(matCount<=3) send(">>>>>> de9dc0 MATERIALIZA (#"+matCount+")"); } });
Interceptor.attach(A(RVA.a9fd00), {
  onEnter:function(a){
    try{
      var nh=a[2].toUInt32();
      if(a[0].toInt32()===1 && nh!==0){
        var g=gCountPtr.readPointer(); var ctxArr=g.add(0x108).readPointer();
        ctxArr.add(0x50).add(0x48).writeU32(nh);
      }
    }catch(e){}
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

      if(phase===0){
        // FASE 0: preparar figura y contexto (una vez, hasta que la entidad exista)
        pA.add(0x10).writeU32(P2_AVATAR); pA.add(0x58).writeU32(POSX); pA.add(0x5C).writeU32(0);
        pB.add(0x10).writeU32(0); pB.add(0x58).writeU32(0); pB.add(0x5C).writeU32(0);
        mgr.add(0x845).writeU8(0); mgr.add(0x880).writeU8(0); mgr.add(0x88c).writeU8(0);
        mgr.add(0x84b).writeU8(0); mgr.add(0x84c).writeU8(0);
        mgr.add(0x867).writeU8(1);
        mgr.add(0x83a).writeU8(1);
        if(g.add(0x94).readU32()<2) g.add(0x94).writeU32(2);
        if(mgr.add(0xcc).readS32() === -1){
          var ctxArr = g.add(0x108).readPointer(); var ctx1 = ctxArr.add(0x50);
          ctx1.add(0x10).writeU32(1);
          ctx1.add(0x48).writeU32(0x1);
          try{ ctx1.add(0x20).writeU8(ctxArr.add(0x20).readU8()); }catch(e){}
          mgr.add(0xcc).writeU32(1);
        }
        // cuando la entidad ya existe, pasar a FASE 1 (estabilizar)
        if(mgr.add(0x64).readS32() !== -1){
          phase = 1;
          send(">>> entidad creada (idx1="+mgr.add(0x64).readS32()+"). Pasando a FASE 1: estabilizar (parar bucle).");
        }
      } else if(phase===1){
        // FASE 1: esperar a la PRIMERA materializacion, luego CONGELAR
        pA.add(0x10).writeU32(P2_AVATAR); pA.add(0x58).writeU32(POSX); pA.add(0x5C).writeU32(0);
        pB.add(0x10).writeU32(0); pB.add(0x58).writeU32(POSX); pB.add(0x5C).writeU32(0);
        if(g.add(0x94).readU32()<2) g.add(0x94).writeU32(2);
        // congelar SOLO cuando el ciclo de creacion se ha COMPLETADO (state vuelve a 0 tras materializar)
        // asi el avatar queda solido/activo, no a medias (fantasma)
        if(matCount >= 1 && mgr.add(0x900).readS32() === 0){
          phase = 2;
          send(">>> ciclo de creacion COMPLETADO (state=0, mat#="+matCount+"). FASE 2: CONGELAR.");
        }
      } else if(phase===2){
        // FASE 2: CONGELAR con mgr+0x87f+slot=1 (mgr+0x880 para slot 1).
        // Este flag bloquea la re-creacion en e01890 (linea 419) SIN marcar el slot como
        // "pausa" (mgr+0x845), asi que el input del mando deberia SEGUIR activo.
        // El avatar YA es solido (de9dc0 corrio en state 4 con mgr+0xd1!=0).
        mgr.add(0x845).writeU8(0);          // NO pausa (mantener mando)
        mgr.add(0x880).writeU8(1);          // mgr+0x87f+slot(1) -> bloquea re-creacion del slot 1
        // NO tocar state ni figura (dejar el avatar solido tal cual)
        if(g.add(0x94).readU32()<2) g.add(0x94).writeU32(2);
        var ctxArr3 = g.add(0x108).readPointer();
        if(ctxArr3.add(0x50).add(0x10).readU32() !== 1) ctxArr3.add(0x50).add(0x10).writeU32(1);
      }
    }catch(e){ send("err: "+e); }
  }
});

setInterval(function(){
  if(mgr){ try{
    var g=gCountPtr.readPointer(); var ctxArr=g.add(0x108).readPointer();
    send("POLL phase="+phase+" count="+g.add(0x94).readU32()+" idx1="+mgr.add(0x64).readS32()
      +" state1(0x900)="+mgr.add(0x900).readS32()+" mat#="+matCount
      +" ctx1+0x10="+ctxArr.add(0x50).add(0x10).readU32()+" ctx1+0x48=0x"+ctxArr.add(0x50).add(0x48).readU32().toString(16));
  }catch(e){} }
}, 1500);

send("final_shot4 instalado (crear UNA vez + estabilizar). Estate quieto en el Toy Box.");
'''

def on_msg(m,d):
    print(m['payload'] if m['type']=='send' else m, flush=True)

s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(1)
except KeyboardInterrupt: pass
