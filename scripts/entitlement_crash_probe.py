import frida, sys, time

# ============================================================================
# SONDA: por que crashea "mi coleccion" bajo TARGET_WIN33 con entitlements:[]
#  (1) Exception handler: captura la DIRECCION EXACTA del crash (RVA del exe),
#      operacion (read/write), puntero accedido, registros y backtrace.
#      -> RVA + 0x400000 = direccion en Ghidra para ver que esperaba el codigo.
#  (2) WinHttpReadData: captura el CUERPO que el juego lee del stub (entitlement),
#      para confirmar que recibe nuestro JSON y con que se queda.
# El juego esta PARCHEADO a WIN33. Lanzalo, entra en "mi coleccion", y crashea:
# la sonda registra el punto de fallo ANTES de que muera.
# ============================================================================

PROC = "DisneyInfinity3.exe"
print("Esperando el juego (lanzalo desde Steam)...", flush=True)
while True:
    try:
        session = frida.attach(PROC); break
    except frida.ProcessNotFoundError:
        time.sleep(0.2)
print("Enganchado. Instalando sonda... entra en 'mi coleccion' cuando estes dentro.", flush=True)

JS = r'''
function mainBase(){
  var mods = Process.enumerateModules();
  for (var i=0;i<mods.length;i++){ if(/DisneyInfinity3\.exe/i.test(mods[i].name)) return mods[i]; }
  return mods[0];
}
var EXE = mainBase();
send("[i] exe base = " + EXE.base + "  size=0x" + EXE.size.toString(16));

function rva(addr){
  try{
    if(addr.compare(EXE.base) >= 0 && addr.compare(EXE.base.add(EXE.size)) < 0)
      return "DI3.exe+0x" + addr.sub(EXE.base).toString(16) + " (Ghidra 0x" + addr.sub(EXE.base).add(0x400000).toString(16) + ")";
    var m = Process.findModuleByAddress(addr);
    if(m) return m.name + "+0x" + addr.sub(m.base).toString(16);
  }catch(e){}
  return addr.toString();
}

// ---------- (1) EXCEPTION HANDLER ----------
Process.setExceptionHandler(function(d){
  try{
    var c = d.context;
    send("========== CRASH ==========");
    send("tipo: " + d.type);
    send("PC (instruccion que falla): " + rva(c.pc));
    if(d.memory){ send("accede a: " + d.memory.address + "  op=" + d.memory.operation); }
    send("regs: eax="+c.eax+" ebx="+c.ebx+" ecx="+c.ecx+" edx="+c.edx);
    send("      esi="+c.esi+" edi="+c.edi+" ebp="+c.ebp+" esp="+c.esp);
    // bytes de la instruccion que falla
    try{ send("bytes@PC: " + hexdump(c.pc, {length:16, header:false, ansi:false})); }catch(e){}
    // backtrace (quien llamo)
    try{
      var bt = Thread.backtrace(c, Backtracer.FUZZY);
      var lines = [];
      for(var i=0;i<bt.length && i<20;i++) lines.push("   " + rva(bt[i]));
      send("backtrace:\n" + lines.join("\n"));
    }catch(e){ send("bt err: "+e); }
    send("========== FIN CRASH ==========");
  }catch(e){ send("handler err: "+e); }
  return false; // dejar que el crash siga (ya lo hemos registrado)
});
send("[ok] exception handler instalado.");

// ---------- (2) capturar el cuerpo del entitlement que lee el juego ----------
var hooked = {};
function findExp(name){ var mods=Process.enumerateModules(); for(var i=0;i<mods.length;i++){ try{ var p=mods[i].findExportByName(name); if(p) return p; }catch(e){} } return null; }
function hook(name, cb){
  if(hooked[name]) return;
  var p = findExp(name);
  if(p){ try{ Interceptor.attach(p, cb); hooked[name]=1; send("[hook] "+name+" OK"); return; }catch(e){ send("[hook] "+name+" err "+e); return; } }
  setTimeout(function(){ hook(name, cb); }, 100);
}

// WinHttpReadData(hRequest, lpBuffer, dwNumberOfBytesToRead, lpdwNumberOfBytesRead)
hook('WinHttpReadData', {
  onEnter:function(a){ this.buf=a[1]; this.pRead=a[3]; },
  onLeave:function(r){
    try{
      if(this.buf.isNull()) return;
      var n = 0;
      try{ n = this.pRead.isNull()? 0 : this.pRead.readU32(); }catch(e){}
      if(n<=0) return;
      var txt = "";
      try{ txt = this.buf.readUtf8String(Math.min(n, 1200)); }catch(e){ try{ txt = this.buf.readAnsiString(Math.min(n,1200)); }catch(e2){} }
      if(txt && /entitle|status|token|url_inf|profile|save/i.test(txt)){
        send(">>> WinHttpReadData ("+n+" bytes): " + txt.slice(0,1000));
      }
    }catch(e){}
  }
});

send("[ok] sonda lista. Entra en 'mi coleccion'.");
'''

def on_msg(m, data):
    if m['type'] == 'send':
        print(m['payload'], flush=True)
    else:
        print("[frida] " + str(m), flush=True)

script = session.create_script(JS)
script.on('message', on_msg)
script.load()
print("== corriendo == (Ctrl+C para salir)", flush=True)
try:
    while True: time.sleep(0.5)
except KeyboardInterrupt:
    pass
