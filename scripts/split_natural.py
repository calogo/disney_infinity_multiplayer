import frida, time

# ============================================================================
# PANTALLA PARTIDA POR LA VIA NATURAL (Sesion 9) — enfoque CORRECTO v2
# ----------------------------------------------------------------------------
# Descubrimiento (ver HANDOFF, FUN_018b0c60):
#   El game loop calcula el modo split: iVar5 = (*PTR_FUN_020129f4)() -> STUB
#   FUN_00969b60 (return 0) = el candado de PC.
#   Solo cuando el modo CALCULADO != modo actual el juego hace TODO junto:
#     1. FUN_006663e0(modo, ...)   -> fija _DAT_020117a8 y numViewports
#     2. dispara "SplitScreenChange"
#     3. dispara "GamePlaySplitScreenChange"  <- reconfigura el RENDER
#   Con el stub en 0, el paso 1 nunca corre (numViewports se queda en 1).
#   [Prueba previa: con 2 jugadores el juego forzo modoHUD=9 y disparo el
#    evento, pero numViewports siguio en 1 porque FUN_006663e0 no se llamo.]
# SOLUCION: parchear los BYTES del stub para que devuelva SPLIT_MODE en eax.
#   xor eax,eax; ret  (33 C0 C3)  ->  mov eax,MODE; ret  (B8 MODE 00 00 00 C3)
#   Con eso el modo calculado = MODE != 0, y el game loop dispara la cadena
#   natural completa (viewports + eventos). Es lo que hara el mod DLL final.
# ----------------------------------------------------------------------------
# SPLIT_MODE: 2 = vertical duro (izq/der, facil de VER).  9 = combinado Toy Box.
# ============================================================================

PROC = "DisneyInfinity3.exe"
SPLIT_MODE = 2

session = frida.attach(PROC)

JS = r'''
var SPLIT_MODE = %d;
var base = Process.getModuleByName("DisneyInfinity3.exe").base;
var modsize = Process.getModuleByName("DisneyInfinity3.exe").size;
function A(rva){ return base.add(rva); }
function rvaOf(addr){
  try{ var o=addr.sub(base); if(o.compare(ptr(modsize))<0 && o.compare(ptr(0))>=0) return "RVA "+o; }catch(e){}
  return addr.toString();
}

var RVA = { e01890:0xA01890, a9fd00:0x69FD00, ce7e70:0x8E7E70, de9dc0:0x9E9DC0 };
var STUB = base.add(0x569B60);                // FUN_00969b60 (stub COMPARTIDO: xor eax,eax; ret) - NO tocar
var PTR_calcMode = base.add(0x1C129F4);       // PTR_FUN_020129f4 (0x020129f4-0x400000) puntero al calc de modo
var DAT_splitMode    = base.add(0x01C117A8);  // _DAT_020117a8 (modo split efectivo)
var DAT_hudMode      = base.add(0x01C117B0);  // DAT_020117b0  (modo split HUD)
var DAT_numViewports = base.add(0x01C59D60);  // DAT_02059d60  (nº viewports)
var gCountPtr        = base.add(0x1E5F540);   // DAT_0225f540
var DAT_introFlag    = base.add(0x01E0191C);  // bypass candado 1-jugador
var P2_AVATAR = 0xf431d, POSX = 0x10000;

var mgr=null, frames=0, newHandle=0, patchDone=false, crashed=false, frozenMsg=false, camDone=false, patchFrame=0;
var de9Count=0, de9Fixed=0;
var cam0Addr=null, cam1Addr=null, add10Log=0, updCallers={}, updHooked=false, camFedMsg=false;
var DAT_camListHead = base.add(0x1E8E8E4);   // DAT_0228e8e4 (0x0228e8e4-0x400000) cabeza lista camaras, next en +0x1c0
// --- seguimiento de camara vía GESTOR (FUN_018adcf0): eye=mgr+0x3c..0x44, target=mgr+0x48..0x50 ---
var camMgr=null, curCam=null, ahsokaET=null, camPocMsg=false, dc1Cam0=0, dc1Cam1=0, mickeyPos=null, mickeyEnt=null, etLogged=false;
var FOLLOW_MICKEY = false;   // false = inyecta vista de cam0 (prueba render); true = desvia a Mickey
function injectMickey(){
  camMgr.add(0x3c).writeByteArray(ahsokaET);   // primero la vista de Ahsoka (estado valido)
  var aeX=camMgr.add(0x3c).readFloat(), aeY=camMgr.add(0x40).readFloat(), aeZ=camMgr.add(0x44).readFloat();
  var atX=camMgr.add(0x48).readFloat(), atY=camMgr.add(0x4c).readFloat(), atZ=camMgr.add(0x50).readFloat();
  var ofX=aeX-atX, ofY=aeY-atY, ofZ=aeZ-atZ;   // offset camara->avatar de Ahsoka
  camMgr.add(0x48).writeFloat(mickeyPos.x); camMgr.add(0x4c).writeFloat(mickeyPos.y); camMgr.add(0x50).writeFloat(mickeyPos.z);
  camMgr.add(0x3c).writeFloat(mickeyPos.x+ofX); camMgr.add(0x40).writeFloat(mickeyPos.y+ofY); camMgr.add(0x44).writeFloat(mickeyPos.z+ofZ);
}
// resolver un handle empaquetado a su entidad+posicion, como hace el juego (FUN_00492e20)
var resolveHandle = new NativeFunction(A(0x92E20), 'pointer', ['pointer','pointer']);
function mickeyWorldPos(){
  try{
    var outp = Memory.alloc(16); var hp = Memory.alloc(4); hp.writeU32(newHandle);
    var r = resolveHandle(outp, hp);
    if(r.isNull()) return null;
    var ent = r.add(8).readPointer();
    if(ent.isNull()) return null;
    return { ent:ent, x:ent.add(0x2c).readFloat(), y:ent.add(0x30).readFloat(), z:ent.add(0x34).readFloat() };
  }catch(e){ return null; }
}

// Callback que sustituye SOLO al puntero de calculo de modo (no al stub compartido).
// Guardado en variable de script para que el GC no lo recoja.
var calcModeCb = new NativeCallback(function(){ return SPLIT_MODE; }, 'int', []);

function camsArray(){
  var out=[], c=DAT_camListHead.readPointer(), i=0;
  while(!c.isNull() && i<8){ out.push(c); c=c.add(0x1c0).readPointer(); i++; }
  return out;
}
function fhex(addr,off){ try{ return addr.add(off).readFloat().toFixed(2); }catch(e){ return "?"; } }
function dumpCamList(tag){
  try{
    var cams = camsArray();
    send("   ["+tag+"] cabeza="+DAT_camListHead.readPointer()+" totalCams="+cams.length+" numViewports="+DAT_numViewports.readU32()+" modoSplit="+DAT_splitMode.readU32());
    for(var i=0;i<cams.length;i++){
      var c=cams[i];
      var v="     cam#"+i+" @"+c;
      try{ v+=" +0x2c(act)="+c.add(0x2c).readU8(); }catch(e){}
      try{ v+=" +0x1d0(id)=0x"+c.add(0x1d0).readU32().toString(16); }catch(e){}
      try{ v+=" +0x158=0x"+c.add(0x158).readU32().toString(16)+" +0x15c=0x"+c.add(0x15c).readU32().toString(16); }catch(e){}
      v+=" pos(+0xc0..c8)=["+fhex(c,0xc0)+","+fhex(c,0xc4)+","+fhex(c,0xc8)+"]";
      send(v);
    }
  }catch(e){ send("   dumpCamList err: "+e); }
}
function copyCamMatrix(){
  // PoC: copiar la matriz de vista de cam0 a cam1 cada frame. Si el panel derecho
  // deja de mostrar el cielo -> el render del 2o viewport va bien, solo faltaba la matriz.
  try{
    var cams=camsArray();
    if(cams.length<2) return;
    Memory.copy(cams[1].add(0xc0), cams[0].add(0xc0), 0x78);  // +0xc0..+0x138 (matrices de vista)
  }catch(e){}
}
function dumpCamDiff(){
  try{
    var cams=camsArray();
    if(cams.length<2){ send(">>> diff: <2 camaras"); return; }
    var c0=cams[0], c1=cams[1];
    send(">>> DIFF cam0(sigue Ahsoka) vs cam1(cielo) — offsets u32 que difieren [0x00..0x200]:");
    var diffs=0;
    for(var off=0; off<0x200; off+=4){
      var v0,v1;
      try{ v0=c0.add(off).readU32(); v1=c1.add(off).readU32(); }catch(e){ continue; }
      if(v0!==v1){
        // marcar si parecen punteros (a heap del juego)
        var p0 = (v0>0x10000 && v0<0x80000000) ? "*" : " ";
        var p1 = (v1>0x10000 && v1<0x80000000) ? "*" : " ";
        send("   +0x"+off.toString(16)+": cam0="+p0+"0x"+v0.toString(16)+"   cam1="+p1+"0x"+v1.toString(16));
        diffs++;
      }
    }
    send(">>> ("+diffs+" offsets difieren)");
  }catch(e){ send(">>> dumpCamDiff err: "+e); }
}
function assignCam1(){
  try{
    var cams = camsArray();
    if(cams.length < 2){ send(">>> solo hay "+cams.length+" camara(s); no puedo asignar cam1."); return; }
    var c0=cams[0], c1=cams[1];
    var a0_158=c0.add(0x158).readU32(), a0_15c=c0.add(0x15c).readU32();
    send(">>> cam0(jugador1) +0x158=0x"+a0_158.toString(16)+" +0x15c=0x"+a0_15c.toString(16));
    send(">>> cam1(jugador2) ANTES +0x158=0x"+c1.add(0x158).readU32().toString(16)+" +0x15c=0x"+c1.add(0x15c).readU32().toString(16));
    // vincular cam1 al avatar del jugador 2 (handle empaquetado capturado)
    c1.add(0x158).writeU32(newHandle);
    c1.add(0x15c).writeU32(newHandle);
    send(">>> cam1 asignada al avatar jugador2 (0x"+newHandle.toString(16)+"). MIRA EL PANEL DERECHO.");
  }catch(e){ send(">>> assignCam1 err: "+e); }
}

Process.setExceptionHandler(function(det){
  if(crashed) return false;
  crashed = true;
  try{
    var c = det.context;
    send("!!!!! CRASH pc="+rvaOf(det.address)+" type="+det.type);
    if(det.memory) send("      acceso "+det.memory.operation+" @ "+det.memory.address);
    send("      eax="+c.eax+" ecx="+c.ecx+" edx="+c.edx+" ebx="+c.ebx);
    send("      esi="+c.esi+" edi="+c.edi+" ebp="+c.ebp+" esp="+c.esp);
    // volcar objeto en ecx (this en fastcall) y su vtable
    try{ send("      [ecx]="+c.ecx.readPointer()); }catch(e){}
    try{ send("      [eax]="+c.eax.readPointer()); }catch(e){}
    dumpCamList("EN CRASH");
  }catch(e){ send("handler err: "+e); }
  return false;
});

// DIAGNÓSTICO: update por-camara del game loop. FUN_018add10 se llama por cada camara;
// hace  if((char)cam[0xB0]!=0) (**vtable+0xc)()  = metodo update de la camara.
// Capturamos, para cam0 (funciona) y cam1 (cielo): su [0xB0] y si procede al update.
Interceptor.attach(A(0x14ADD10), {   // FUN_018add10 (dispatcher del update por-camara)
  onEnter:function(){
    if(cam1Addr===null) return;
    var c=this.context.ecx;
    if(c.equals(cam1Addr)){
      try{
        // FORZAR el gate: poner el byte bajo de cam1[0xB0] a 1 para que su update SIEMPRE corra
        var b0 = c.add(0xB0).readU32();
        if((b0 & 0xff) === 0){ c.add(0xB0).writeU32(b0 | 1); }
        if(add10Log<5){ send("   [add10] cam1 [0xB0]=0x"+b0.toString(16)+" -> forzado byte bajo a 1 (update SÍ)"); add10Log++; }
      }catch(e){}
    }
  }
});

// Capturar el puntero del GESTOR de camaras (lo devuelve FUN_018adcf0).
Interceptor.attach(A(0x14ADCF0), {   // FUN_018adcf0
  onLeave:function(retval){ if(camMgr===null && !retval.isNull()){ camMgr = ptr(retval.toString()); } }
});

// INYECCIÓN DE VISTA: FUN_016dc1d0 (sub del update de camara) LEE del gestor el eye
// (mgr+0x3c..0x44) y el target (mgr+0x48..0x50) al empezar. Durante el update de cam0
// capturamos esos 6 floats (framing de Ahsoka); durante el de cam1 los inyectamos ANTES
// de que la funcion los lea -> cam1 renderiza esa vista. (curCam lo pone el hook del updFn.)
Interceptor.attach(A(0x12DC1D0), {   // FUN_016dc1d0
  onEnter:function(){
    if(camMgr===null || curCam===null || cam0Addr===null) return;
    try{
      if(curCam.equals(cam0Addr)){
        ahsokaET = camMgr.add(0x3c).readByteArray(0x18);   // eye(3) + target(3) floats
        dc1Cam0++;
      } else if(cam1Addr!==null && curCam.equals(cam1Addr) && ahsokaET){
        if(FOLLOW_MICKEY && mickeyPos){
          // eye = Mickey + offset de camara de Ahsoka ; target = Mickey
          var eX=camMgr.add(0x3c), eY=camMgr.add(0x40), eZ=camMgr.add(0x44);
          var tX=camMgr.add(0x48), tY=camMgr.add(0x4c), tZ=camMgr.add(0x50);
          // primero pon la vista de Ahsoka (para FOV/estado), luego desplaza a Mickey
          camMgr.add(0x3c).writeByteArray(ahsokaET);
          var aeX=eX.readFloat(), aeY=eY.readFloat(), aeZ=eZ.readFloat();
          var atX=tX.readFloat(), atY=tY.readFloat(), atZ=tZ.readFloat();
          var ofX=aeX-atX, ofY=aeY-atY, ofZ=aeZ-atZ;
          tX.writeFloat(mickeyPos.x); tY.writeFloat(mickeyPos.y); tZ.writeFloat(mickeyPos.z);
          eX.writeFloat(mickeyPos.x+ofX); eY.writeFloat(mickeyPos.y+ofY); eZ.writeFloat(mickeyPos.z+ofZ);
        } else {
          camMgr.add(0x3c).writeByteArray(ahsokaET);   // vista de Ahsoka tal cual
        }
        dc1Cam1++;
        if(!camPocMsg){ camPocMsg=true; send(">>> inyeccion activa (FOLLOW_MICKEY="+FOLLOW_MICKEY+"). MIRA EL PANEL DERECHO."); }
      }
    }catch(e){ if(!camPocMsg){ camPocMsg=true; send(">>> err inyeccion: "+e); } }
  }
});

// FIX SÓLIDO+CÁMARA: en de9dc0 (materializa avatar), para el slot 1 limpiar el bit de
// PROXY/fantasma (avatar+0x39 & 2). Con el bit a 0, de9dc0 toma el camino SÓLIDO y ademas
// llama a ce7e70 (vincula avatar->camara del jugador 2). Un solo bit arregla las 2 cosas.
Interceptor.attach(A(RVA.de9dc0), {
  onEnter:function(){
    try{
      var sp = this.context.esp;
      var slot = sp.add(4).readU32();
      var avatar = sp.add(8).readPointer();
      if(slot === 1){
        var f = avatar.add(0x39).readU8();
        if(de9Count < 6) send(">>> de9dc0 slot1 avatar="+avatar+" +0x39=0x"+f.toString(16)+((f&2)?" (PROXY/fantasma)":" (solido)"));
        if(f & 2){ avatar.add(0x39).writeU8(f & 0xFD); de9Fixed++; }   // limpiar bit proxy -> solido + bind camara
        de9Count++;
      }
    }catch(e){ if(de9Count<3) send("de9 err: "+e); }
  }
});

// FIX del avatar en la vinculacion de camara (para que la 2a camara enfoque al jugador 2)
Interceptor.attach(A(RVA.ce7e70), {
  onEnter:function(){
    var sp=this.context.esp;
    if(sp.add(4).readU32()===1 && sp.add(8).readU32()===0 && newHandle!==0){ sp.add(8).writeU32(newHandle); }
  }
});
Interceptor.attach(A(RVA.a9fd00), {
  onEnter:function(a){
    try{ var nh=a[2].toUInt32(); if(a[0].toInt32()===1 && nh!==0){
      newHandle = nh;
      var g=gCountPtr.readPointer(); g.add(0x108).readPointer().add(0x50).add(0x48).writeU32(nh);
    }}catch(e){}
  }
});

function repointCalc(){
  var before = PTR_calcMode.readPointer();
  send(">>> PTR_calcMode (0x1C129F4) ANTES = "+before+"   (stub esperado @ "+STUB+")");
  if(!before.equals(STUB)){
    send("   (aviso: el puntero no apunta al stub esperado; sigo igualmente)");
  }
  try{ Memory.protect(PTR_calcMode, Process.pointerSize, 'rw-'); }catch(e){ send("   (protect: "+e+")"); }
  PTR_calcMode.writePointer(calcModeCb);
  send(">>> PTR_calcMode AHORA = "+PTR_calcMode.readPointer()+"  -> callback que devuelve "+SPLIT_MODE);
  send(">>> SOLO FUN_018b0c60 vera modo="+SPLIT_MODE+" (el stub compartido sigue en 0). Cadena NATURAL. MIRA LA PANTALLA.");
  return true;
}

Interceptor.attach(A(RVA.e01890), {
  onEnter:function(){
    if(mgr===null){ mgr=this.context.ecx; send("mgr="+mgr); }
    try{ DAT_introFlag.writeU32(1); }catch(e){}
    frames++;
    if(frames < 90) return;
    try{
      var g=gCountPtr.readPointer();
      if(g.add(0x94).readU32()<2) g.add(0x94).writeU32(2);   // playerCount siempre = 2
      if(newHandle === 0){
        // FASE 1: aun materializando -> pedir union / spawn (SOLO hasta que Mickey exista)
        var pA=mgr.add(0xC).readPointer(), pB=mgr.add(0x8).readPointer();
        pA.add(0x10).writeU32(P2_AVATAR); pA.add(0x58).writeU32(POSX); pA.add(0x5C).writeU32(0);
        pB.add(0x10).writeU32(0); pB.add(0x58).writeU32(0); pB.add(0x5C).writeU32(0);
        mgr.add(0x845).writeU8(0); mgr.add(0x880).writeU8(0); mgr.add(0x88c).writeU8(0);
        mgr.add(0x84b).writeU8(0); mgr.add(0x84c).writeU8(0);
        mgr.add(0x867).writeU8(1); mgr.add(0x83a).writeU8(1);
        if(mgr.add(0xcc).readS32() === -1){
          var ctxArr = g.add(0x108).readPointer(); var ctx1 = ctxArr.add(0x50);
          ctx1.add(0x10).writeU32(1); ctx1.add(0x48).writeU32(0x1);
          try{ ctx1.add(0x20).writeU8(ctxArr.add(0x20).readU8()); }catch(e){}
          mgr.add(0xcc).writeU32(1);
          send(">>> jugador 2 activado.");
        }
      } else {
        // FASE 2: Mickey YA existe -> SOLIDIFICAR (skip slot) para que deje de re-crearse
        // en bucle y quede SÓLIDO (hallazgo sesion 7: mgr+0x845=1 solidifica el avatar).
        mgr.add(0x845).writeU8(1);   // skip slot -> avatar solido, fin del bucle de creacion
        mgr.add(0x83a).writeU8(0);   // apagar solicitud de union pendiente
        if(!frozenMsg){ frozenMsg=true; send(">>> Mickey materializado; SOLIDIFICO (mgr+0x845=1) y congelo la peticion."); }
      }
      // Con el jugador 2 materializado, REPUNTAR el calc de modo UNA vez.
      if(!patchDone && frames > 170 && newHandle !== 0){
        patchDone = true;
        patchFrame = frames;
        send(">>> jugador 2 con handle 0x"+newHandle.toString(16)+". Repuntando el puntero de calculo de modo...");
        repointCalc();
      }
      // Ya con el split activo y las camaras creadas: volcar y vincular cam1 al jugador 2.
      if(patchDone && !camDone && frames > patchFrame + 40){
        camDone = true;
        var cams = camsArray();
        dumpCamList("con split activo");
        if(cams.length >= 2){
          cam0Addr = cams[0]; cam1Addr = cams[1];
          var vt0 = cams[0].readPointer(), vt1 = cams[1].readPointer();
          send(">>> cam0 vtable="+rvaOf(vt0)+"   cam1 vtable="+rvaOf(vt1)+"   ("+(vt0.equals(vt1)?"MISMA clase de camara":"CLASES DISTINTAS ***")+")");
          try{
            var updFn = vt0.add(0xc).readPointer();
            send(">>> update fn de cam0 (vtable+0xc) = "+rvaOf(updFn)+"  -> hookeada (snapshot/inyeccion via gestor)");
            Interceptor.attach(updFn, {
              onEnter:function(){
                curCam = this.context.ecx; var k=curCam.toString(); updCallers[k]=(updCallers[k]||0)+1;
                if(camMgr===null) return;
                try{
                  // diagnostico: loguear el eye/target del gestor durante cam0 y cam1
                  if(!etLogged && cam0Addr && curCam.equals(cam0Addr)){ etLogged=true;
                    send(">>> [cam0] gestor eye=["+camMgr.add(0x3c).readFloat().toFixed(1)+","+camMgr.add(0x40).readFloat().toFixed(1)+","+camMgr.add(0x44).readFloat().toFixed(1)+"] target=["+camMgr.add(0x48).readFloat().toFixed(1)+","+camMgr.add(0x4c).readFloat().toFixed(1)+","+camMgr.add(0x50).readFloat().toFixed(1)+"]");
                  }
                }catch(e){}
              }
            });
            updHooked = true;
          }catch(e){ send(">>> err hook updFn: "+e); }
        }
      }
      // LEVER DIRECTO: habilitar en cam1 el seguimiento-por-handle de FUN_018b9e40.
      // Ese bloque (gated por cam+0x1b4) resuelve cam+0x158 (handle) -> posicion del avatar
      // -> fija el target de la camara. Poniendo +0x1b4=1 y +0x158=Mickey, cam1 lo sigue.
      if(camDone && cam1Addr){
        try{
          cam1Addr.add(0x1b4).writeU8(1);              // habilitar seguimiento por handle
          cam1Addr.add(0x158).writeU32(newHandle);     // handle de Mickey
          cam1Addr.add(0x15c).writeU32(newHandle);
          if(!camFedMsg){ camFedMsg=true; send(">>> cam1+0x1b4=1 y +0x158=Mickey (0x"+newHandle.toString(16)+"). Su update deberia seguir a Mickey. MIRA EL PANEL DERECHO."); }
        }catch(e){ if(!camFedMsg){ camFedMsg=true; send(">>> err lever: "+e); } }
      }
    }catch(e){}
  }
});

// log periodico del estado (para confirmar que la cadena natural fija los viewports)
var n=0;
var iv = setInterval(function(){
  n++;
  if(!camDone) return;
  try{
    send("   estado t"+n+": camMgr="+(camMgr?camMgr:"null")+" | FUN_016dc1d0 cam0="+dc1Cam0+" cam1="+dc1Cam1+" | mickeyPos="+(mickeyPos?("["+mickeyPos.x.toFixed(1)+","+mickeyPos.y.toFixed(1)+","+mickeyPos.z.toFixed(1)+"]"):"n/a"));
  }catch(e){}
}, 1500);

send("split_natural v2 instalado (modo "+SPLIT_MODE+"). Materializa jugador 2 y parchea el stub -> cadena NATURAL de split. Estate quieto en Toy Box.");
''' % SPLIT_MODE

def on_msg(m,d):
    print(m['payload'] if m['type']=='send' else m, flush=True)

s=session.create_script(JS); s.on('message',on_msg); s.load()
print("== corriendo ==",flush=True)
try:
    while True: time.sleep(1)
except KeyboardInterrupt: pass
