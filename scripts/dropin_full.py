import frida, time

# CO-OP COMPLETO: drop-in (join real: mando+viewport+split) + forzado de avatar (cuerpo solido).
# El drop-in se llama en cuanto se localiza el gameLoop (hilo Frida, como en dropin_join, que funciono).
# Al unirse P2 arranca la creacion -> e01890 tiquea -> forzamos su avatar y CONGELAMOS (solido).

PROC = "DisneyInfinity3.exe"
P2_SKU = 0xf431d   # Mickey
print("Esperando el juego...", flush=True)
while True:
    try: session = frida.attach(PROC); break
    except frida.ProcessNotFoundError: time.sleep(0.2)
print("Enganchado.", flush=True)

JS = r'''
var P2_SKU = __P2SKU__;
var base = Process.getModuleByName("DisneyInfinity3.exe").base;
function rebase(x){ return base.add(x - 0x400000); }
function pat(np){ var v=np.toUInt32()>>>0, s=""; for(var i=0;i<4;i++){ var b=((v>>>(i*8))&0xff).toString(16); if(b.length<2)b="0"+b; s+=(i?" ":"")+b; } return s; }
var gCountPtr=base.add(0x1E5F540), introFlag=base.add(0x1E0191C);
var POSX=0x10000;

var gamePlayers=null, gameLoop=null, dropCalled=false;
try{ var opAddr=base.add(0x69E3CF+2).readU32(); gamePlayers=ptr(ptr(opAddr).readU32()); }catch(e){}
if(gamePlayers){ try{ gamePlayers.add(0x98).writeU8(1); }catch(e){} }

var dropInFn = new NativeFunction(base.add(0x69B020), 'void', ['pointer','int'], 'thiscall');
var getPrim = new NativeFunction(base.add(0xF80740), 'int', ['pointer'], 'thiscall');
var getSec  = new NativeFunction(base.add(0xF806E0), 'int', ['pointer','int'], 'thiscall');
function secondId(){ try{ return getSec(gamePlayers, getPrim(gamePlayers)); }catch(e){ return -9; } }

var vt0=rebase(0x1D4418C), vt58=rebase(0x1D44180), vt308=rebase(0x1D44174), vt378=rebase(0x1D43F88);
function scanGameLoop(){ if(gameLoop) return true;
  try{ var ranges=Process.enumerateRanges('rw-');
    for(var i=0;i<ranges.length && !gameLoop;i++){ var hits;
      try{ hits=Memory.scanSync(ranges[i].base, ranges[i].size, pat(vt0)); }catch(e){ continue; }
      for(var j=0;j<hits.length;j++){ var o=hits[j].address;
        try{ if(o.add(0x58).readU32()===vt58.toUInt32() && o.add(0x308).readU32()===vt308.toUInt32() && o.add(0x378).readU32()===vt378.toUInt32()){ gameLoop=o; break; } }catch(e){}
      }
    }
  }catch(e){}
  return !!gameLoop;
}

function doDropIn(){
  if(dropCalled) return;
  if(!scanGameLoop()){ send("gameLoop no encontrado aun, reintentando..."); setTimeout(doDropIn, 1500); return; }
  send(">>> gameLoop="+gameLoop);
  try{ gamePlayers.add(0x98).writeU8(1); dropInFn(gameLoop, 1); dropCalled=true;
       send(">>> DROP-IN llamado (P2 se une). secondPlayerId="+secondId()+"  <-- MIRA LA PANTALLA (split)");
  }catch(e){ send("err dropIn: "+e); setTimeout(doDropIn, 1500); }
}

var mgr=null, frames=0, newHandle=0, joinMsg=false;

// solidificar avatar del slot 1
Interceptor.attach(base.add(0x9E9DC0), { onEnter:function(){ try{
  var sp=this.context.esp, slot=sp.add(4).readU32(), av=sp.add(8).readPointer();
  if(slot===1){ var f=av.add(0x39).readU8(); if(f&2) av.add(0x39).writeU8(f&0xFD); }
}catch(e){} }});
// dd19e0 onLeave: capturar handle del slot 1
Interceptor.attach(base.add(0x9D19E0), {
  onEnter:function(){ try{ this.slot=this.context.esp.add(4).readU32(); }catch(e){ this.slot=-1; } },
  onLeave:function(r){ try{ if(this.slot===1){ var h=r.toUInt32(); if(h>0x100000 && h!==0xffffffff && newHandle===0){ newHandle=h; } } }catch(e){} }
});

// e01890: materializar el avatar de P2 (tiquea cuando hay creacion, tras el drop-in)
Interceptor.attach(base.add(0xA01890), {
  onEnter:function(){
    if(mgr===null){ mgr=this.context.ecx; send("mgr="+mgr+" (e01890 tiqueando)"); }
    if(!dropCalled) return;
    frames++;
    try{ introFlag.writeU32(1);
      var g=gCountPtr.readPointer();
      if(g.add(0x94).readU32()<2) g.add(0x94).writeU32(2);
      if(newHandle===0){ var hx=mgr.add(0x64).readU32(); if(hx>0x100000 && hx!==0xffffffff) newHandle=hx; }
      // FASE 1 = disparar el spawn SOLO los primeros ~45 frames; luego CONGELAR (rompe el bucle)
      if(newHandle===0 && frames < 45){
        var pA=mgr.add(0xC).readPointer(), pB=mgr.add(0x8).readPointer();
        pA.add(0x10).writeU32(P2_SKU); pA.add(0x58).writeU32(POSX); pA.add(0x5C).writeU32(0);
        pB.add(0x10).writeU32(0); pB.add(0x58).writeU32(0); pB.add(0x5C).writeU32(0);
        mgr.add(0x845).writeU8(0); mgr.add(0x880).writeU8(0); mgr.add(0x88c).writeU8(0);
        mgr.add(0x84b).writeU8(0); mgr.add(0x84c).writeU8(0);
        mgr.add(0x867).writeU8(1); mgr.add(0x83a).writeU8(1);
        if(mgr.add(0xcc).readS32()===-1){
          var ctxArr=g.add(0x108).readPointer(), ctx1=ctxArr.add(0x50);
          ctx1.add(0x10).writeU32(1); ctx1.add(0x48).writeU32(0x1);
          try{ ctx1.add(0x20).writeU8(ctxArr.add(0x20).readU8()); }catch(e){}
          mgr.add(0xcc).writeU32(1);
        }
      } else {
        // CONGELAR: solidificar y dejar de re-disparar (rompe el bucle de spawn)
        mgr.add(0x845).writeU8(1); mgr.add(0x83a).writeU8(0);
        if(!joinMsg){ joinMsg=true; send(">>> CONGELADO (fin del bucle). handle=0x"+newHandle.toString(16)+" frames="+frames); }
      }
    }catch(e){}
  }
});

var t=0; setInterval(function(){ t++; send("   t"+t+": secondPlayerId="+secondId()+" mgr="+(mgr?"ok":"no")+" newHandle=0x"+newHandle.toString(16)+(newHandle!==0?" SOLIDO":"")); }, 1500);
send("dropin_full instalado (gamePlayers="+gamePlayers+"). Estate en Toy Box.");
setTimeout(doDropIn, 300);
'''.replace('__P2SKU__', str(P2_SKU))
def on_msg(m,d): print(m['payload'] if m['type']=='send' else m, flush=True)
s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(0.5)
except KeyboardInterrupt: pass
