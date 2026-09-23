import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceManager;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;

// Para cada NOMBRE (arg): localiza el string, busca quien lo referencia (la tabla
// nombre->funcion), y lee los punteros vecinos para revelar el puntero a funcion.
public class FindReg extends GhidraScript {
    boolean isCode(Address a){
        try {
            var block = currentProgram.getMemory().getBlock(a);
            return block != null && block.isExecute();
        } catch(Exception e){ return false; }
    }
    String funcAt(Address a){
        FunctionManager fm = currentProgram.getFunctionManager();
        Function f = fm.getFunctionContaining(a);
        if(f!=null) return f.getName()+" @ "+f.getEntryPoint();
        return null;
    }
    @Override
    public void run() throws Exception {
        String[] names = getScriptArgs();
        Memory mem = currentProgram.getMemory();
        ReferenceManager rm = currentProgram.getReferenceManager();
        Address base = currentProgram.getImageBase();
        for(String name : names){
            println("\n==================== " + name + " ====================");
            byte[] pat = (name + "\0").getBytes("US-ASCII");
            Address sAddr = mem.findBytes(base, pat, null, true, monitor);
            if(sAddr == null){ println("  [string no encontrado]"); continue; }
            println("  string @ " + sAddr);
            Reference[] refs;
            var it = rm.getReferencesTo(sAddr);
            int nref = 0;
            while(it.hasNext()){
                Reference r = it.next();
                Address from = r.getFromAddress();
                nref++;
                println("  <- ref desde " + from + (isCode(from)?" (codigo)":" (datos)"));
                // leer punteros vecinos (tabla: [ ..., pFunc, pName, ... ] o [ pName, pFunc ])
                for(int k=-2;k<=3;k++){
                    try{
                        Address slot = from.add((long)k*4);
                        int val = mem.getInt(slot);
                        Address p = base.getNewAddress(val & 0xffffffffL);
                        if(isCode(p)){
                            String fn = funcAt(p);
                            println(String.format("      [%+d] %s -> CODE %s%s", k, slot, p, fn!=null? "  ==> "+fn : ""));
                        }
                    }catch(Exception e){}
                }
                if(isCode(from)){
                    String fn = funcAt(from);
                    if(fn!=null) println("      (ref en funcion " + fn + ")");
                }
                if(nref>=6) { println("  ... (mas refs omitidas)"); break; }
            }
            if(nref==0) println("  [sin referencias]");
        }
        println("\n#### FIN ####");
    }
}
