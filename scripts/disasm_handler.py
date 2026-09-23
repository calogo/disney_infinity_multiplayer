import frida, time
PROC = "DisneyInfinity3.exe"
session = frida.attach(PROC)
JS = r'''
var base = Process.getModuleByName("DisneyInfinity3.exe").base;
function rvaOf(p){ try{ var o=p.sub(base); if(o.compare(ptr(0))>=0 && o.compare(ptr(0x3000000))<0) return "RVA 0x"+o.toString(16);}catch(e){} return ""+p; }
function disasm(name, method, n){
  send("== "+name+" @ "+method+" ("+rvaOf(method)+") ==");
  var p=method;
  for(var i=0;i<n;i++){ try{ var ins=Instruction.parse(p);
    var ex=""; if(ins.mnemonic==="call"){ try{ ex=" -> "+rvaOf(ptr(ins.opStr)); }catch(e){} }
    send("  "+rvaOf(p)+"  "+ins.mnemonic+" "+ins.opStr+ex);
    p=ins.next; if(ins.mnemonic==="ret"||ins.mnemonic==="jmp") break;
  }catch(e){ send("  parse err: "+e); break; } }
}
// DAT_02140194 (obj) -> vtable -> metodos
var obj = ptr(base.add(0x1D40194).readU32());
var vt = ptr(obj.readU32());
send("obj(DAT_02140194)="+obj+"  vtable="+vt+" ("+rvaOf(vt)+")");
disasm("LockPlayerToController [vt+0x7c]", ptr(vt.add(0x7c).readU32()), 40);
disasm("GetLockedControllerIndex [vt+?] via thunk 0x154bbe0", (function(){
  // thunk 0x154bbe0: mov eax,[ecx]; jmp [eax+off] -> leer el offset
  try{ var t=base.add(0x114bbe0); var ins=Instruction.parse(t); var ins2=Instruction.parse(ins.next);
    var m=ins2.opStr.match(/0x[0-9a-f]+/); var off=m?parseInt(m[0],16):0;
    send("(GetLocked thunk salta a vt+0x"+off.toString(16)+")");
    return ptr(vt.add(off).readU32());
  }catch(e){ send("thunk err "+e); return ptr(0); }
})(), 40);
send("== fin ==");
'''
def on_msg(m,d): print(m['payload'] if m['type']=='send' else m, flush=True)
s=session.create_script(JS); s.on('message',on_msg); s.load()
time.sleep(2)
