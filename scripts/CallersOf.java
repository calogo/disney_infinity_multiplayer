import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceManager;
import java.util.HashSet;
import java.util.Set;

// Para cada direccion (entrada de funcion), lista quien la llama y decompila
// cada funcion llamante (dedup), para ver como se obtiene el 'this'.
public class CallersOf extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        DecompInterface dif = new DecompInterface();
        dif.openProgram(currentProgram);
        FunctionManager fm = currentProgram.getFunctionManager();
        ReferenceManager rm = currentProgram.getReferenceManager();
        for (String a : args) {
            Address addr = currentProgram.getAddressFactory().getAddress(a);
            println("\n########## CALLERS de " + a + " ##########");
            Set<String> seen = new HashSet<String>();
            var it = rm.getReferencesTo(addr);
            int n = 0;
            while (it.hasNext()) {
                Reference r = it.next();
                Address from = r.getFromAddress();
                Function fn = fm.getFunctionContaining(from);
                if (fn == null) { println("  ref desde " + from + " (sin funcion)"); continue; }
                String ep = fn.getEntryPoint().toString();
                if (seen.contains(ep)) continue;
                seen.add(ep);
                n++;
                println("\n=== llamante " + fn.getName() + " @ " + ep + " (llama desde " + from + ") ===");
                DecompileResults res = dif.decompileFunction(fn, 90, monitor);
                if (res != null && res.decompileCompleted())
                    println(res.getDecompiledFunction().getC());
                else
                    println("   [decompile fallo]");
                if (n >= 3) { println("  ... (mas llamantes omitidos)"); break; }
            }
            if (n == 0) println("  [sin llamantes directos]");
        }
        println("\n#### FIN ####");
    }
}
