import frida, time

# FASE 2a del TITERE: materializar a Mickey (P2) SOLIDO y MOVERLO con el mando 2.
# Reutiliza la receta probada de split_natural.py (materializar+solidificar) y le
# anade: leer el stick del mando 2 (XInput idx 1) y escribir la posicion de Mickey
# (entidad+0x2c/0x34) cada frame -> Mickey se desliza segun el stick. PoC visible
# en la MISMA pantalla (no hace falta split todavia).

PROC = "DisneyInfinity3.exe"
print("Esperando el juego...", flush=True)
while True:
    try: session = frida.attach(PROC); break
    except frida.ProcessNotFoundError: time.sleep(0.2)
print("Enganchado.", flush=True)

JS = r'''
var base = Process.getModuleByName("DisneyInfinity3.exe").base;
var modsize = Process.getModuleByName("DisneyInfinity3.exe").size;
function A(rva){ return base.add(rva); }
function rvaOf(a){ try{ var o=a.sub(base); if(o.compare(ptr(modsize))<0 && o.compare(ptr(0))>=0) return "RVA "+o; }catch(e){} return ""+a; }

var RVA = { e01890:0xA01890, de9dc0:0x9E9DC0, a9fd00:0x69FD00, resolve:0x92E20 };
var gCountPtr    = base.add(0x1E5F540);
var DAT_introFlag= base.add(0x01E0191C);
var P2_AVATAR = 0xf431d, POSX = 0x10000;

var mgr=null, frames=0, newHandle=0, crashed=false, frozenMsg=false;
var mickeyEnt=null, mickeyPosOff=0, p1Ent=null, placed=false, mickeyAvatar=null, dbgDone=false;
var camMgr=null, foundMsg=false;

var resolveHandle = new NativeFunction(A(RVA.resolve), 'pointer', ['pointer','pointer']);
var resolveDbg=false;
function entOf(handle){
  try{ var outp=Memory.alloc(16), hp=Memory.alloc(4); hp.writeU32(handle);
    outp.writeU32(0); outp.add(4).writeU32(0); outp.add(8).writeU32(0); outp.add(0xc).writeU32(0);
    var r=resolveHandle(outp,hp);
    if(!resolveDbg){ resolveDbg=true;
      try{ send(">>> DBG resolve(h=0x"+handle.toString(16)+"): r="+r+"  outp[0..c]=0x"+outp.readU32().toString(16)+" 0x"+outp.add(4).readU32().toString(16)+" 0x"+outp.add(8).readU32().toString(16)+" 0x"+outp.add(0xc).readU32().toString(16)); }catch(e){ send("DBG err "+e); }
    }
    if(r.isNull()) return null;
    var e=r.add(8).readPointer(); return e.isNull()?null:e; }catch(e){ if(!resolveDbg){resolveDbg=true; send(">>> DBG resolve EXCEPTION: "+e);} return null; }
}

// --- XInput mando 2 ---
var XInputGetState=null, xibuf=Memory.alloc(20);
(function findXI(){ var mods=Process.enumerateModules();
  for(var i=0;i<mods.length;i++){ try{ var p=mods[i].findExportByName("XInputGetState"); if(p){ XInputGetState=new NativeFunction(p,'uint32',['uint32','pointer']); send("XInput @ "+mods[i].name); return; } }catch(e){} }
  setTimeout(findXI,300);
})();
function pad2(){ if(!XInputGetState) return null; var r=XInputGetState(1,xibuf); if(r!==0) return null;
  return { btn:xibuf.add(4).readU16(), lx:xibuf.add(10).readS16(), ly:xibuf.add(12).readS16() }; }

Process.setExceptionHandler(function(d){ if(crashed) return false; crashed=true;
  try{ send("!!! CRASH "+rvaOf(d.address)+" "+d.type+(d.memory?(" "+d.memory.operation+" @ "+d.memory.address):"")); }catch(e){} return false; });

// solidificar el avatar del slot 1 (limpiar bit proxy)
Interceptor.attach(A(RVA.de9dc0), { onEnter:function(){ try{
  var sp=this.context.esp, slot=sp.add(4).readU32(), av=sp.add(8).readPointer();
  if(slot===1){ var f=av.add(0x39).readU8(); if(f&2) av.add(0x39).writeU8(f&0xFD);
    if(mickeyAvatar===null){ mickeyAvatar=av; send("mickeyAvatar="+av); } }
}catch(e){} }});

// capturar el gestor de camara (su target = posicion del avatar seguido = Hulk/P1)
Interceptor.attach(A(0x14ADCF0), { onLeave:function(rv){ if(camMgr===null && !rv.isNull()){ camMgr=ptr(rv.toString()); } }});

// capturar el handle del avatar de P2
Interceptor.attach(A(RVA.a9fd00), { onEnter:function(a){ try{
  var nh=a[2].toUInt32(); if(a[0].toInt32()===1 && nh!==0){ newHandle=nh;
    var g=gCountPtr.readPointer(); g.add(0x108).readPointer().add(0x50).add(0x48).writeU32(nh); }
}catch(e){} }});

var SPEED = 0.25;  // unidades por frame (ajustable)
Interceptor.attach(A(RVA.e01890), {
  onEnter:function(){
    if(mgr===null){ mgr=this.context.ecx; send("mgr="+mgr); }
    try{ DAT_introFlag.writeU32(1); }catch(e){}
    frames++;
    if(frames<90) return;
    try{
      var g=gCountPtr.readPointer();
      if(g.add(0x94).readU32()<2) g.add(0x94).writeU32(2);
      // si el jugador 2 YA existe (handle VALIDO, no basura tipo 0x8), usarlo
      if(newHandle===0){ var hx=mgr.add(0x64).readU32(); if(hx>0x100000 && hx!==0xffffffff){ newHandle=hx; send(">>> P2 ya existia; uso handle 0x"+hx.toString(16)); } }
      if(newHandle===0){
        // FASE 1: materializar
        var pA=mgr.add(0xC).readPointer(), pB=mgr.add(0x8).readPointer();
        pA.add(0x10).writeU32(P2_AVATAR); pA.add(0x58).writeU32(POSX); pA.add(0x5C).writeU32(0);
        pB.add(0x10).writeU32(0); pB.add(0x58).writeU32(0); pB.add(0x5C).writeU32(0);
        mgr.add(0x845).writeU8(0); mgr.add(0x880).writeU8(0); mgr.add(0x88c).writeU8(0);
        mgr.add(0x84b).writeU8(0); mgr.add(0x84c).writeU8(0);
        mgr.add(0x867).writeU8(1); mgr.add(0x83a).writeU8(1);
        if(mgr.add(0xcc).readS32()===-1){
          var ctxArr=g.add(0x108).readPointer(), ctx1=ctxArr.add(0x50);
          ctx1.add(0x10).writeU32(1); ctx1.add(0x48).writeU32(0x1);
          try{ ctx1.add(0x20).writeU8(ctxArr.add(0x20).readU8()); }catch(e){}
          mgr.add(0xcc).writeU32(1); send(">>> jugador 2 activado.");
        }
      } else {
        // FASE 2: solidificar
        mgr.add(0x845).writeU8(1); mgr.add(0x83a).writeU8(0);
        if(!frozenMsg){ frozenMsg=true; send(">>> Mickey materializado y SOLIDO. handle=0x"+newHandle.toString(16)); }
        // MOVER a Mickey con el mando 2 (usa el campo de posicion hallado por correlacion)
        if(mickeyEnt && mickeyPosOff){
          var p=pad2();
          if(p && (Math.abs(p.lx)>9000 || Math.abs(p.ly)>9000)){
            try{
              var x=mickeyEnt.add(mickeyPosOff).readFloat(), z=mickeyEnt.add(mickeyPosOff+8).readFloat();
              x += (p.lx/32767)*SPEED;
              z -= (p.ly/32767)*SPEED;
              mickeyEnt.add(mickeyPosOff).writeFloat(x);
              mickeyEnt.add(mickeyPosOff+8).writeFloat(z);
            }catch(e){}
          }
        }
      }
    }catch(e){}
  }
});

// FINDER: localizar la posicion de Mickey por CORRELACION con la de Hulk (target de la camara)
function isHeap(p){ try{ return !p.isNull() && p.compare(ptr("0x100000"))>0 && p.compare(ptr("0x40000000"))<0; }catch(e){ return false; } }
function near(v,ref){ return isFinite(v) && Math.abs(v-ref)<80.0; }
function scanTriple(obj, maxOff, hx, hz){
  for(var o=0;o<=maxOff;o+=4){ try{ var a=obj.add(o).readFloat(), b=obj.add(o+4).readFloat(), c=obj.add(o+8).readFloat();
    if(near(a,hx) && near(c,hz) && isFinite(b)) return o; }catch(e){} }
  return -1;
}
var n=0;
setInterval(function(){ n++;
  // posicion de Hulk (target del gestor de camara)
  var hx=null,hy=null,hz=null;
  if(camMgr){ try{ hx=camMgr.add(0x48).readFloat(); hy=camMgr.add(0x4c).readFloat(); hz=camMgr.add(0x50).readFloat(); }catch(e){} }
  if(!mickeyEnt && mickeyAvatar && hx!==null && isFinite(hx)){
    // buscar en el avatar y en sus punteros (2 niveles) un trio cerca de Hulk
    var found=false;
    var o0=scanTriple(mickeyAvatar,0x400,hx,hz);
    if(o0>=0){ mickeyEnt=mickeyAvatar; mickeyPosOff=o0; found=true; }
    if(!found){ for(var o2=0;o2<=0x300 && !found;o2+=4){ try{ var p=mickeyAvatar.add(o2).readPointer(); if(isHeap(p)){
      var oo=scanTriple(p,0x200,hx,hz); if(oo>=0){ mickeyEnt=p; mickeyPosOff=oo; found=true; } } }catch(e){} } }
    if(found){ send(">>> POSICION DE MICKEY hallada: obj="+mickeyEnt+" +0x"+mickeyPosOff.toString(16)+" = ("+mickeyEnt.add(mickeyPosOff).readFloat().toFixed(1)+","+mickeyEnt.add(mickeyPosOff+4).readFloat().toFixed(1)+","+mickeyEnt.add(mickeyPosOff+8).readFloat().toFixed(1)+")  Hulk=("+hx.toFixed(1)+","+hy.toFixed(1)+","+hz.toFixed(1)+"). MUEVE EL STICK DEL MANDO 2."); }
  }
  if(mickeyEnt && mickeyPosOff){ try{ send("   t"+n+": MickeyPos=["+mickeyEnt.add(mickeyPosOff).readFloat().toFixed(1)+","+mickeyEnt.add(mickeyPosOff+8).readFloat().toFixed(1)+"] (mueve stick mando2)"); }catch(e){} }
  else { send("   t"+n+": buscando pos... camMgr="+(camMgr?"ok":"no")+" mickeyAvatar="+(mickeyAvatar?"ok":"no")+" Hulk="+(hx!==null&&isFinite(hx)?("("+hx.toFixed(0)+","+hz.toFixed(0)+")"):"?")); }
}, 2000);

send("puppet_p2 instalado. Estate DENTRO de una Toy Box, quieto. Se materializa Mickey y lo mueves con el MANDO 2.");
'''
def on_msg(m,d): print(m['payload'] if m['type']=='send' else m, flush=True)
s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(0.5)
except KeyboardInterrupt: pass
