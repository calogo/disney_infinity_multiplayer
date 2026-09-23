import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;
import ghidra.program.model.symbol.SymbolTable;

// Resuelve nombres de simbolo -> direccion + RVA + decompilacion.
public class FindSym extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] names = getScriptArgs();
        DecompInterface dif = new DecompInterface();
        dif.openProgram(currentProgram);
        SymbolTable st = currentProgram.getSymbolTable();
        FunctionManager fm = currentProgram.getFunctionManager();
        for (String name : names) {
            SymbolIterator it = st.getSymbols(name);
            if (!it.hasNext()) { println("\n#### " + name + " NO ENCONTRADO ####"); continue; }
            Symbol s = it.next();
            Address a = s.getAddress();
            long rva = a.getOffset() - 0x400000L;
            println("\n#### " + name + " @ " + a + "  (RVA 0x" + Long.toHexString(rva) + ") ####");
            Function fn = fm.getFunctionAt(a);
            if (fn == null) fn = fm.getFunctionContaining(a);
            if (fn != null) {
                DecompileResults res = dif.decompileFunction(fn, 90, monitor);
                if (res != null && res.decompileCompleted())
                    println(res.getDecompiledFunction().getC());
                else println("  [decompile fallo]");
            } else println("  (sin funcion en esa direccion)");
        }
        println("\n#### FIN ####");
    }
}
