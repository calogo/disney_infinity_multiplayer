import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressFactory;
import ghidra.util.task.ConsoleTaskMonitor;
import java.util.HashSet;
import java.util.Set;

public class DecompileAt extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        DecompInterface dif = new DecompInterface();
        dif.openProgram(currentProgram);
        FunctionManager fm = currentProgram.getFunctionManager();
        AddressFactory af = currentProgram.getAddressFactory();
        Set<String> seen = new HashSet<String>();
        for (String a : args) {
            Address addr;
            try { addr = af.getAddress(a); } catch (Exception e) { println("BAD ADDR " + a); continue; }
            Function fn = fm.getFunctionContaining(addr);
            if (fn == null) { println("\n#### NO FUNC at " + a + " ####"); continue; }
            String ep = fn.getEntryPoint().toString();
            if (seen.contains(ep)) { println("\n#### (dup) " + a + " en " + fn.getName() + " @ " + ep); continue; }
            seen.add(ep);
            println("\n#### FUNC " + fn.getName() + " @ " + ep + "  (contiene " + a + ") ####");
            DecompileResults res = dif.decompileFunction(fn, 120, new ConsoleTaskMonitor());
            if (res != null && res.decompileCompleted()) {
                println(res.getDecompiledFunction().getC());
            } else {
                println("   [decompile fallo]");
            }
        }
        println("\n#### FIN ####");
    }
}
