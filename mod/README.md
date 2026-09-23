# Disney Infinity 3.0 (PC / Steam) — Local Split-Screen Co-op mod

A single native proxy DLL that restores **local 2-player split-screen co-op** on the PC
port of *Disney Infinity 3.0: Gold Edition* — working in the **Toy Box AND in Play Sets**
(story worlds), with **live character selection for Player 2**.

No Python, no Frida, no external runtime. Just one DLL. It only reads/writes the running
process memory — it does **not** touch saves, online, or achievements, and it's fully
reversible.

> Built by combining two reverse-engineering projects:
> **CrabeLoader / DisneyInfinity-SplitScreenMods (LucasLhomme)** for the Player-2 *join*
> groundwork, and this project for the **Player-2 spawn + body materialization +
> character load + selector**. See CREDITS.

---

## What it does
- Press **START on controller 2** in a Toy Box or a Play Set → Player 2 joins:
  split screen, its own camera, its own controller, solid body.
- Press **LB + RB together on controller 2** → Player 2 **changes character** live
  (cycles through the built-in list; the model is loaded properly).
- Player 2's **starting** character is read from `coop_p2.txt` (a SKU; see
  `CHARACTERS_SKU.txt`). Default is Anakin (`f4308`).

## Requirements
- Disney Infinity 3.0: Gold Edition (PC / Steam), legit copy.
- Two XInput controllers (Xbox-style).

## Install (1 minute)
1. Copy these files into the game folder (next to `DisneyInfinity3.exe`), typically
   `...\Steam\steamapps\common\Disney Infinity 3.0 Gold Edition\`:
   - `coop_bink2w32.dll`
   - `coop_p2.txt`
   - `INSTALL.bat`, `UNINSTALL.bat`
2. With the game **closed**, run **`INSTALL.bat`** (it backs up the original
   `bink2w32.dll` as `_bink2w32_orig.dll` and drops the proxy in).
3. Launch the game normally.

**Uninstall:** run `UNINSTALL.bat` (or Steam → Verify integrity of game files).

## How to play
1. Enter a Toy Box or a Play Set with 2 controllers connected.
2. **START on controller 2** → Player 2 joins.
3. **LB+RB on controller 2** → change Player 2's character.
4. In a Play Set, only that franchise's characters are valid — cycle to a valid one
   (e.g. in a Star Wars world use Ahsoka/Anakin/ObiWan/Yoda/DarthMaul).

## Notes / known
- The character cycler rotates through ALL characters (not filtered per world yet).
- Changing Player 2's character can briefly flash Player 1 as a "materializing" ghost;
  it resolves by itself and Player 1 stays fully playable.
- Built for the current Steam Gold Edition build.

## How it works (short)
The proxy `bink2w32.dll` forwards all 77 Bink exports to the renamed original
(`_bink2w32_orig.dll`) and starts a thread. On START (controller 2) it runs, in the game's
own memory: resolve the players container → find the game loop → call the drop-in creator
(the real join) → materialize Player 2's body → resolve the chosen character's item and
call the game's character-apply to **load the model**. LB+RB re-materializes the body with
the next character. Full addresses, offsets and the exact call chain are in
**`RECIPE_FOR_CRABELOADER.md`**; the full source is in **`src/coop.c`**.

Build (with Zig, portable): `zig cc -target x86-windows-gnu -shared -O2 -o bink2w32.dll coop.c bink2w32.def -lkernel32`

## Credits
- **[LucasLhomme](https://github.com/LucasLhomme)** — CrabeLoader,
  DisneyInfinity-SplitScreenMods, CrabeMenu. The Player-2 join method (drop-in / viewport /
  split), `GameStandAloneLoop`, `LockPlayerToController`, and the `SetCharacter` /
  `ForceUnlockData` character API this project cross-checked against.
- This project — Player-2 spawn + body materialization, the sku→item resolution and the
  native character-load call, and the proxy-DLL mod that ties it together with a
  START trigger and an LB+RB character selector.

## Legal / ethics
Educational, non-commercial interoperability research on a legitimate copy, for local play.
Ships no game code or assets and defeats no DRM. Disney Infinity and its marks belong to
their owners. Use at your own risk.
