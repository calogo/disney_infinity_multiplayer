import frida, time

# Encuentra el OFFSET de la posicion vigilando que campo CAMBIA cuando se mueve un avatar.
# Engancha el resolver (FUN_00492e20 RVA 0x92E20, thiscall) para capturar entidades tipo 0x30.
# Muestrea floats de cada entidad; cuando el usuario MUEVE a Hulk (mando 1), el offset que
# cambia con valores tipo-coordenada = la POSICION. Mickey usa el mismo offset.

PROC = "DisneyInfinity3.exe"
print("Esperando el juego...", flush=True)
while True:
    try: session = frida.attach(PROC); break
    except frida.ProcessNotFoundError: time.sleep(0.2)
print("Enganchado.", flush=True)

JS = r'''
var base = Process.getModuleByName("DisneyInfinity3.exe").base;
var RESOLVE = base.add(0x92E20);
var ents = {};       // entPtr(str) -> {ptr, prev:{off:val}}
var order = [];
var MAXENT = 14, LO=0x0, HI=0x200;

Interceptor.attach(RESOLVE, {
  onEnter:function(a){ this.h=0; try{ var h=a[1].readU32(); if((h>>>24)===0x30) this.h=h; }catch(e){} },
  onLeave:function(r){ if(this.h===0||r.isNull()) return;
    try{ var e=r.add(8).readPointer(); if(e.isNull()) return; var k=e.toString();
      if(!ents[k] && order.length<MAXENT){ ents[k]={ptr:e, prev:null, handle:this.h}; order.push(k); }
    }catch(ex){} }
});

function coord(v){ return isFinite(v) && Math.abs(v)>0.2 && Math.abs(v)<100000; }
var n=0;
setInterval(function(){ n++;
  var report=[];
  for(var i=0;i<order.length;i++){ var o=ents[order[i]]; var cur={};
    for(var off=LO; off<=HI; off+=4){ try{ cur[off]=o.ptr.add(off).readFloat(); }catch(e){} }
    if(o.prev){
      var ch=[];
      for(var off2=LO; off2<=HI; off2+=4){ var a=o.prev[off2], b=cur[off2];
        if(a!==undefined && b!==undefined && a!==b && (coord(a)||coord(b)) && Math.abs(b-a)>0.3){ ch.push("+0x"+off2.toString(16)+"("+a.toFixed(1)+"->"+b.toFixed(1)+")"); }
      }
      if(ch.length>0) report.push("ent"+i+" h=0x"+o.handle.toString(16)+" "+o.ptr+" CAMBIA: "+ch.join(" "));
    }
    o.prev=cur;
  }
  if(report.length>0){ send(">>> t"+n+" CAMBIOS (mueve Hulk!):"); report.forEach(function(x){ send("   "+x); }); }
  else send("   t"+n+": "+order.length+" entidades vigiladas, sin cambios (MUEVE A HULK con el mando 1)");
}, 1500);
send("change_finder instalado. MUEVE A HULK con el mando 1 (adelante/atras/lados) para localizar el offset de posicion.");
'''
def on_msg(m,d): print(m['payload'] if m['type']=='send' else m, flush=True)
s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(0.5)
except KeyboardInterrupt: pass
