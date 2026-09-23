import frida, time

# Captura la POSICION real de Mickey enganchandose al resolver de handles del juego.
# FUN_00492e20 (RVA 0x92E20) __thiscall(ecx=tablaHandles, param2_out, param3=&handle):
#   decodifica el handle y DEVUELVE el slot; entidad = [ret+8]; posicion = entidad+0x2c/0x30/0x34.
# NO materializa (Mickey ya existe en la sesion del split) -> sin crash de estado sucio.
# Lee el handle de P2 de mgr+0x64. Cuando el juego resuelve ESE handle, capturamos todo.

PROC = "DisneyInfinity3.exe"
print("Esperando el juego...", flush=True)
while True:
    try: session = frida.attach(PROC); break
    except frida.ProcessNotFoundError: time.sleep(0.2)
print("Enganchado.", flush=True)

JS = r'''
var base = Process.getModuleByName("DisneyInfinity3.exe").base;
var RESOLVE = base.add(0x92E20), E01890 = base.add(0xA01890);
var mgr=null, tableThis=null;
var avatars={};   // handle -> entidad

Interceptor.attach(E01890, { onEnter:function(){ if(mgr===null){ mgr=this.context.ecx; send("mgr="+mgr); } }});

// hook al resolver: capturar handles tipo avatar (0x30xxxxxx)
Interceptor.attach(RESOLVE, {
  onEnter:function(a){
    this.h=0;
    try{ var h=a[1].readU32(); if((h>>>24)===0x30){ this.h=h; this.tbl=this.context.ecx; } }catch(e){}
  },
  onLeave:function(r){
    if(this.h===0) return;
    if(tableThis===null){ tableThis=this.tbl; send(">>> tabla handles (this) = "+tableThis); }
    try{ if(!r.isNull()){ var ent=r.add(8).readPointer();
      if(!ent.isNull()){ avatars[this.h]=ent; } } }catch(e){}
  }
});

var n=0;
setInterval(function(){ n++;
  var ks=Object.keys(avatars);
  if(ks.length===0){ send("   t"+n+": aun sin avatares resueltos"); return; }
  var line="   t"+n+": ";
  for(var i=0;i<ks.length;i++){ var e=avatars[ks[i]];
    try{ line+="h="+ks[i]+"->("+e.add(0x2c).readFloat().toFixed(1)+","+e.add(0x30).readFloat().toFixed(1)+","+e.add(0x34).readFloat().toFixed(1)+")  "; }catch(ex){ line+="h="+ks[i]+"->inv "; } }
  send(line);
}, 2000);
send("resolve_pos instalado (sin materializar). Estate en la Toy Box con Mickey ya creado.");
'''
def on_msg(m,d): print(m['payload'] if m['type']=='send' else m, flush=True)
s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(0.5)
except KeyboardInterrupt: pass
