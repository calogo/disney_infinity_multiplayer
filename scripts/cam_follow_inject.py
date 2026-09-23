import frida, time

# Hace que la 2a camara (der, vista a 0) mire a Mickey: copia la matriz de vista de
# cam0 (que sigue a Hulk) a cam1 y la desplaza por el vector Hulk->Mickey.
# Matriz de vista 4x4 en cam+0xc0 (filas de 0x10): R en +0xc0/+0xd0/+0xe0, traslacion en +0xf0.
# translation1 = translation0 - (delta . R). Posiciones de avatar en entidad+0x134.

PROC = "DisneyInfinity3.exe"
session = frida.attach(PROC)
JS = r'''
var base = Process.getModuleByName("DisneyInfinity3.exe").base;
var HEAD = base.add(0x1E8E8E4), RESOLVE = base.add(0x92E20);
var cam0=null, cam1=null, hH=0, mH=0;
var entH=null, entM=null;

function F(p,o){ return p.add(o).readFloat(); }
function W(p,o,v){ p.add(o).writeFloat(v); }

// identificar camaras: cam0 = vista valida (Hulk), cam1 = vista ~0 (der)
var fcDbg=0;
function findCams(){
  try{ var c=HEAD.readPointer(), i=0, dbg=[];
    while(!c.isNull() && i<8){
      var vx=F(c,0xf0), vy=F(c,0xf4), vz=F(c,0xf8);
      var mag=Math.abs(vx)+Math.abs(vy)+Math.abs(vz);
      var hh=c.add(0x158).readU32(); var fl=c.add(0x1b4).readU8();
      dbg.push("cam"+i+"@"+c+" mag="+mag.toFixed(1)+" h=0x"+hh.toString(16)+" 1b4="+fl);
      // cam1 (la de Mickey) = la que tiene el follow activado (1b4=1); cam0 = la otra (Hulk)
      if(fl!==0 && cam1===null){ cam1=c; mH=hh; }
      else if(fl===0 && cam0===null){ cam0=c; hH=hh; }
      c=c.add(0x1c0).readPointer(); i++;
    }
    if(fcDbg<3){ fcDbg++; send("[findCams] "+i+" cams: "+dbg.join(" | ")); }
  }catch(e){ send("findCams err "+e); }
}

Interceptor.attach(RESOLVE, {
  onEnter:function(a){ this.h=0; try{ var h=a[1].readU32(); if(h===hH||h===mH) this.h=h; }catch(e){} },
  onLeave:function(r){ if(this.h===0||r.isNull()) return; try{ var e=r.add(8).readPointer(); if(e.isNull())return;
    if(this.h===hH) entH=e; else if(this.h===mH) entM=e; }catch(e){} }
});

var msg=false;
setInterval(function(){
  if(cam0===null||cam1===null){ findCams(); if(cam0&&cam1) send(">>> cam0(Hulk)="+cam0+" hH=0x"+hH.toString(16)+"  cam1(der)="+cam1+" mH=0x"+mH.toString(16)); return; }
  if(!entM) return;
  try{
    var mx=F(entM,0x134), my=F(entM,0x138), mz=F(entM,0x13c);   // pos de Mickey
    // OJO de la camara: detras y arriba de Mickey (ajustable)
    var OFY=14.0, OFZ=22.0;
    var ex=mx, ey=my+OFY, ez=mz-OFZ;         // eye
    var tx=mx, ty=my+2.0, tz=mz;             // target (mirar un poco por encima del suelo)
    // forward = normalize(target-eye)
    var fx=tx-ex, fy=ty-ey, fz=tz-ez; var fl=Math.sqrt(fx*fx+fy*fy+fz*fz)||1; fx/=fl; fy/=fl; fz/=fl;
    // right = normalize(cross(up, forward)), up=(0,1,0)
    var rx=1*fz-0*fy, ry=0*fx-0*fz, rz=0*fy-1*fx; var rl=Math.sqrt(rx*rx+ry*ry+rz*rz)||1; rx/=rl; ry/=rl; rz/=rl;
    // up2 = cross(forward, right)
    var ux=fy*rz-fz*ry, uy=fz*rx-fx*rz, uz=fx*ry-fy*rx;
    // conservar proyeccion de cam0
    Memory.copy(cam1.add(0xc0), cam0.add(0xc0), 0x78);
    // matriz de vista (row-major, v*M): filas +0xc0/+0xd0/+0xe0, traslacion +0xf0
    W(cam1,0xc0,rx); W(cam1,0xc4,ux); W(cam1,0xc8,fx);
    W(cam1,0xd0,ry); W(cam1,0xd4,uy); W(cam1,0xd8,fy);
    W(cam1,0xe0,rz); W(cam1,0xe4,uz); W(cam1,0xe8,fz);
    W(cam1,0xf0, -(rx*ex+ry*ey+rz*ez));
    W(cam1,0xf4, -(ux*ex+uy*ey+uz*ez));
    W(cam1,0xf8, -(fx*ex+fy*ey+fz*ez));
    if(!msg){ msg=true; send(">>> look-at cam1 a Mickey ["+mx.toFixed(1)+","+my.toFixed(1)+","+mz.toFixed(1)+"] eye=("+ex.toFixed(1)+","+ey.toFixed(1)+","+ez.toFixed(1)+"). MIRA PANEL DERECHO."); }
  }catch(e){ if(!msg){msg=true; send("err inject: "+e);} }
}, 16);
send("cam_follow_inject instalado.");
'''
def on_msg(m,d): print(m['payload'] if m['type']=='send' else m, flush=True)
s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(0.5)
except KeyboardInterrupt: pass
