# Local Co-op (drop-in Player 2) — integration recipe for CrabeLoader

This is the "make Player 2 actually appear" half of local split-screen co-op for
Disney Infinity 3.0 (PC / Steam, Gold Edition). It's the piece CrabeLoader's
split-screen work was missing (the reader never gained a 2nd solid avatar).

All addresses are **RVAs** relative to the module base (ImageBase 0x400000).
At runtime the exe is ASLR-relocated, so use `base + RVA` (base = GetModuleHandle(NULL)).
The 4 vtable addresses used to find the game loop are **Ghidra VAs** (subtract 0x400000
to get the RVA). Verified live many times; the standalone build (proxy bink2w32.dll)
gives 2 solid characters + 2 cameras + split + separate pads, stable.

## The whole sequence (triggered once, e.g. from your menu or a keybind)

1. **Resolve `gamePlayers`** (the players container):
   - `opAddr = readU32(base + 0x69E3D1)`  ← operand of the instruction at RVA 0x69E3CF (+2)
   - `gamePlayers = readU32(opAddr)`
   - `writeU8(gamePlayers + 0x98, 1)`  ← enables drop-in staging

2. **Find `gameLoop`** (GameStandAloneLoop) by scanning committed RW memory for an
   object whose vtable pointers match:
   - `*(obj + 0x00) == base + (0x1D4418C - 0x400000)`
   - `*(obj + 0x58) == base + (0x1D44180 - 0x400000)`
   - `*(obj + 0x308) == base + (0x1D44174 - 0x400000)`
   - `*(obj + 0x378) == base + (0x1D43F88 - 0x400000)`
   (all four must match → that object is the game loop.)

3. **Call the drop-in creator** `FUN_00a9b020` (RVA **0x69B020**), `__thiscall`:
   - `this = gameLoop`, one int arg `= 1`  →  `dropIn(gameLoop, 1)`
   - This is the real join (controller + viewport + split). We call it **directly**,
     bypassing `OnDropInRequest` (0x69E480) whose global gates crash (null deref @ +0xC).
   - After this, `secondPlayerId` goes -1 → 1. Split screen appears.
   - In CrabeLoader: no FFI, so do this via an `installCodeCave` stub:
     `mov ecx, gameLoop; push 1; call FUN_00a9b020; ret` (triggered once).

4. **Materialize P2's body** — needed or the game shows "missing/incorrect figure".
   Install a hook on **`e01890`** (RVA **0xA01890**, `__thiscall`, `this=ecx=mgr`).
   Prologue is 6 relocatable bytes: `55 8B EC 83 E4 F8` (stolenLen = 6).
   Each call, once drop-in was done:
   ```
   writeU32(base + 0x1E0191C, 1)                 // intro/ready flag
   g = readU32(base + 0x1E5F540)                 // players/global object
   if (readU32(g + 0x94) < 2) writeU32(g+0x94,2) // 2 local players
   // FASE 1: first ~45 frames force the spawn, then FREEZE (breaks the respawn loop)
   if (frames < 45 && newHandle == 0):
       pA = readU32(mgr + 0xC); pB = readU32(mgr + 0x8)
       writeU32(pA+0x10, P2_SKU); writeU32(pA+0x58, 0x10000); writeU32(pA+0x5C, 0)
       writeU32(pB+0x10, 0);      writeU32(pB+0x58, 0);       writeU32(pB+0x5C, 0)
       writeU8(mgr+0x845,0); writeU8(mgr+0x880,0); writeU8(mgr+0x88c,0)
       writeU8(mgr+0x84b,0); writeU8(mgr+0x84c,0)
       writeU8(mgr+0x867,1); writeU8(mgr+0x83a,1)
       if (readS32(mgr+0xcc) == -1):
           ctxArr = readU32(g + 0x108); ctx1 = ctxArr + 0x50
           writeU32(ctx1+0x10,1); writeU32(ctx1+0x48,1)
           writeU8(ctx1+0x20, readU8(ctxArr+0x20))
           writeU32(mgr+0xcc,1)
   else:                                         // FREEZE = solid body
       writeU8(mgr+0x845,1); writeU8(mgr+0x83a,0)
   ```
   `P2_SKU` = the chosen character's sku (Mickey = 0x000F431D). With your
   `Game.SetCharacter`, you can set P2's character properly instead of this poke.

5. **Solidify** (optional but cleaner) — hook **`0x9E9DC0`** (RVA, prologue 7 bytes
   `6A FF 68 xx xx xx xx`, stolenLen = 7). On entry: `slot = [esp+4]`, `av = [esp+8]`;
   `if (slot == 1) av[0x39] &= ~2`  (clears a "ghost/transparent" bit on P2's avatar).

## Notes / open item
- Character **sku** lives at `item + 0xC8`; item **name** at `item + 0x40`
  (matches your `Game.ListCharacters`/`SetCharacter` — item iterator is
  `FUN_00d95410` (first) / `FUN_00b4a080` (next)).
- P2's in-game collection stays **locked** (guest profile has no unlock data). Your
  `Game.ForceUnlockData` may cover this; in our tests forcing the store lock predicate
  `FUN_00b7b430` didn't affect P2's in-game roster (different system).
- In a **Play Set**, P2 must be a franchise-valid character or the game shows
  "figure must belong to the current Play Set" — so P2's sku should match the Play Set
  (your menu solves this).

## Credits
Split-screen / join / camera groundwork: CrabeLoader (LucasLhomme).
P2 spawn + materialization recipe above: the calogo / Claude co-op project.

## IMPORTANT finding (P2 character model)
Tested live: our materialization sets P2's sku at `mgr.pA + 0x10` and it PASSES the
Play Set franchise validation (no "wrong figure" dialog with a valid-franchise sku,
e.g. Anakin `0xf4308` in Twilight of the Republic). BUT the avatar renders as a
**white/untextured placeholder** UNLESS that character's model is already streamed in
memory (e.g. it works if P2's sku == P1's current character, whose model is loaded).

=> Our poke sets the id but does NOT trigger the character asset/model LOAD.
   This is exactly what your `Game.SetCharacter(sku, "loadout"/"legacy")` does properly.
   Clean split: **we do the drop-in/join + body materialize; you do the character
   load (SetCharacter) + unlock (ForceUnlockData).** Call SetCharacter for player 2
   right after our drop-in and the model should stream in correctly.

Character sku list confirmed (item+0xC8), e.g. TCW: Ahsoka 0xf430b, Anakin 0xf4308,
ObiWan 0xf4309, Yoda 0xf430a, DarthMaul 0xf430c. Full list in PERSONAJES_SKU.txt.

## HOW THE CHARACTER MODEL LOADS (confirmed via CrabeLoader 11_avatar.lua + our Ghidra)
CrabeLoader's SetCharacter "loadout" route (the same the game's character grid uses):
    VirtualReaderPC_SetCurrentCharacter(coerceSku(sku, playerId))   -- set desired char
    VirtualReaderPC_ActivateChanges(playerId, true)                 -- true = forceAvatarChange -> LOADS MODEL
(legacy route: Players_ForceAvatar / Players_ChangeAvatar — does NOT reload model in a Play Set)

Native chain we mapped (so it can be done without the Lua VM if wanted):
- SetCurrentCharacter handler = TEMP_00b406e0 (RVA 0x406e0): just `*(reader + 0xB0) = item`.
- ActivateChanges handler = FUN_00b83d20 (RVA 0x783d20): if reader+0xB0 != -1, calls
      FUN_00b73060(<this>, item = *(reader+0xB0), force)     <-- APPLY + LOAD
- FUN_00b73060 (RVA 0x373060): `if(this+0x2c != item || force){ unload old (FUN_0042af60);
      this+0x2c = item; FUN_0043a320(item,...) [apply]; if(FUN_00b62750(item)) FUN_00f44dd0(item) [MODEL LOAD]; }`
  => The model streaming is FUN_0043a320 + FUN_00f44dd0 on the item. `item` here is the
     value coerceSku produced (needs sku->item resolution; item has sku at item+0xC8).

### USER-OBSERVED BEHAVIOR (important)
To change Player 1's character, Player 2 must press START — the game does a "refresh" of
the current selection and re-issues the "figure" call (i.e. it runs the ActivateChanges/
forceAvatarChange path). So the START press is effectively what triggers the model reload.
=> A clean co-op character-swap should: set the target's current char, then run the
   ActivateChanges(force=true) path (that START-style refresh) to stream the model in.
