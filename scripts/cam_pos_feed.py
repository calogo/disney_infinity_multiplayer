import frida, time

# Alimenta el FOLLOW nativo de la camara: el juego (FUN_018b9e40) lee la posicion del
# avatar en entidad+0x268 (o +0x2c), NO en +0x134. Para Mickey +0x268 esta a 0 -> camara
# al cielo. Copiamos su posicion real (+0x134) a +0x268/+0x2c cada tick. Sin re-materializar.
# Identifica a Mickey = avatar (tipo 0x30) con +0x134 valido pero +0x268 vacio.

PROC = "DisneyInfinity3.exe"
session = frida.attach(PROC)

JS = r'''
var base = Process.getModuleByName("DisneyInfinity3.exe").base;
var RESOLVE = base.add(0x92E20);
var ents = {}, feed = {};

Interceptor.attach(RESOLVE, {
  onEnter:function(a){ this.h=0; try{ var h=a[1].readU32(); if((h>>>24)===0x30) this.h=h; }catch(e){} },
  onLeave:function(r){ if(this.h===0||r.isNull()) return; try{ var e=r.add(8).readPointer(); if(!e.isNull()) ents[e.toString()]=e; }catch(ex){} }
});

function valid(v){ return isFinite(v) && Math.abs(v)>0.05 && Math.abs(v)<100000; }
var dbgN=0;
setInterval(function(){
  var keys=Object.keys(ents);
  if(dbgN<5){ dbgN++;
    var info=[]; for(var j=0;j<keys.length && j<8;j++){ var ee=ents[keys[j]]; try{ info.push(ee+" p134=("+ee.add(0x134).readFloat().toFixed(1)+","+ee.add(0x13c).readFloat().toFixed(1)+") p268=("+ee.add(0x268).readFloat().toFixed(1)+","+ee.add(0x270).readFloat().toFixed(1)+")"); }catch(e){} }
    send("[dbg] ents="+keys.length+"  "+info.join(" | "));
  }
  for(var k in ents){ var e=ents[k];
    try{
      var x=e.add(0x134).readFloat(), y=e.add(0x138).readFloat(), z=e.add(0x13c).readFloat();
      if(!(valid(x)||valid(z))) continue;   // sin posicion valida (no es avatar activo)
      if(!feed[k]){
        var cx=e.add(0x268).readFloat(), cz=e.add(0x270).readFloat();
        if(!valid(cx) && !valid(cz)){ feed[k]=1; send(">>> Mickey identificado "+e+" pos=("+x.toFixed(1)+","+y.toFixed(1)+","+z.toFixed(1)+") -> alimentando +0x268"); }
      }
      if(feed[k]){
        e.add(0x268).writeFloat(x); e.add(0x26c).writeFloat(y); e.add(0x270).writeFloat(z);
        e.add(0x2c).writeFloat(x);  e.add(0x30).writeFloat(y);  e.add(0x34).writeFloat(z);
      }
    }catch(ex){}
  }
}, 60);
send("cam_pos_feed instalado. Copiando pos de Mickey a +0x268 para el follow de la 2a camara. MIRA EL PANEL DERECHO.");
'''
def on_msg(m,d): print(m['payload'] if m['type']=='send' else m, flush=True)
s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(0.5)
except KeyboardInterrupt: pass
