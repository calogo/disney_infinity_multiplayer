import frida, time

# JOIN NATIVO de P2 replicando el metodo de CrabeLoader (LucasLhomme/DisneyInfinity-SplitScreenMods).
# Su enable(1) hace 3 cosas que dan a P2 mando + viewport + pantalla partida:
#   1. gamePlayers = [[base+0x69E3CF+2]]   (singleton GamePlayers)
#   2. [gamePlayers+0x98] = 1              (forceAllowed: limpia bit de rechazo de DropInCheck)
#   3. OnDropInRequest = callThis1(base+0x69E480, gameLoop, pad=1)   <- EL JOIN
#      gameLoop se localiza por heap-scan de su vtable (base+0x194418C) + verif 4 vtables.
# Necesita un NIVEL cargado (Toy Box), no el menu.

PROC = "DisneyInfinity3.exe"
print("Esperando el juego...", flush=True)
while True:
    try: session = frida.attach(PROC); break
    except frida.ProcessNotFoundError: time.sleep(0.2)
print("Enganchado.", flush=True)

JS = r'''
var base = Process.getModuleByName("DisneyInfinity3.exe").base;
function rebase(x){ return base.add(x - 0x400000); }
function pat(np){ var v=np.toUInt32()>>>0, s=""; for(var i=0;i<4;i++){ var b=((v>>>(i*8))&0xff).toString(16); if(b.length<2)b="0"+b; s+=(i?" ":"")+b; } return s; }

// 1) gamePlayers singleton
var gamePlayers=null;
try{
  var opAddr = base.add(0x69E3CF+2).readU32();      // operando = direccion runtime del global
  gamePlayers = ptr(ptr(opAddr).readU32());
  send("[1] gamePlayers = "+gamePlayers+"  (global @ 0x"+opAddr.toString(16)+")");
}catch(e){ send("err gamePlayers: "+e); }

// 2) gameLoop por heap-scan (vtable en base+0x194418C, verif offsets 0x58/0x308/0x378)
var vt0=rebase(0x1D4418C), vt58=rebase(0x1D44180), vt308=rebase(0x1D44174), vt378=rebase(0x1D43F88);
send("[2dbg] vt0(runtime)="+vt0+" pat='"+pat(vt0)+"'");
var gameLoop=null, rawHits=0, shown=0;
try{
  var ranges=Process.enumerateRanges('rw-'); var scanned=0;
  for(var i=0;i<ranges.length && !gameLoop;i++){
    var hits;
    try{ hits=Memory.scanSync(ranges[i].base, ranges[i].size, pat(vt0)); }catch(e){ continue; }
    scanned++;
    for(var j=0;j<hits.length;j++){ var o=hits[j].address; rawHits++;
      try{ var a=o.add(0x58).readU32(), b=o.add(0x308).readU32(), c=o.add(0x378).readU32();
        if(shown<4){ shown++; send("   hit @"+o+" +0x58=0x"+a.toString(16)+"(esp 0x"+vt58.toUInt32().toString(16)+") +0x308=0x"+b.toString(16)+" +0x378=0x"+c.toString(16)); }
        if(a===vt58.toUInt32() && b===vt308.toUInt32() && c===vt378.toUInt32()){ gameLoop=o; break; }
      }catch(e){}
    }
  }
  send("[2] gameLoop = "+(gameLoop?gameLoop:"NO ENCONTRADO")+"  (rangos="+scanned+" aciertos_vt0="+rawHits+")");
}catch(e){ send("err gameLoop: "+e); }

// 3) forceAllowed + OnDropInRequest
if(gamePlayers && gameLoop){
  try{ gamePlayers.add(0x98).writeU8(1); send("[3a] [gamePlayers+0x98]=1 (forceAllowed) OK"); }catch(e){ send("err forceAllowed: "+e); }
  try{
    var dropIn = new NativeFunction(base.add(0x69B020), 'void', ['pointer','int'], 'thiscall');
    dropIn(gameLoop, 1);   // FUN_00a9b020: encola el drop-in de P2, saltando los gates
    send("[3b] FUN_00a9b020(gameLoop, pad=1) llamado (drop-in DIRECTO). <-- MIRA LA PANTALLA");
  }catch(e){ send("err dropIn directo: "+e); }
}
// vigilar si aparece el 2o jugador
var getPrim = new NativeFunction(base.add(0xF80740), 'int', ['pointer'], 'thiscall');
var getSec  = new NativeFunction(base.add(0xF806E0), 'int', ['pointer','int'], 'thiscall');
function secondId(){ try{ var p=getPrim(gamePlayers); return getSec(gamePlayers,p); }catch(e){ return "err"; } }
send("== drop-in lanzado; vigilando P2 (secondId ahora = "+secondId()+") ==");
var t=0; var iv=setInterval(function(){ t++;
  var s=secondId();
  send("   t"+t+": secondPlayerId="+s+(typeof s==="number"&&s>0?"  <-- P2 EXISTE!!":""));
  if(t>=12) clearInterval(iv);
}, 1000);
'''
def on_msg(m,d): print(m['payload'] if m['type']=='send' else m, flush=True)
s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(0.5)
except KeyboardInterrupt: pass
