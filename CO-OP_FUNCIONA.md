# ✅ CO-OP LOCAL DE 2 JUGADORES — FUNCIONANDO

**Confirmado en vivo, con foto:** 2 personajes sólidos (Hulk P1 + Mickey P2), 2 cámaras
independientes, pantalla partida vertical, **mandos separados** (cada stick mueve solo a su
jugador), estable. Es el primer co-op local jugable conseguido en el port de PC de DI3.

Se logró **combinando dos proyectos complementarios**:
- El **join nativo** (mando + viewport + split) del método de
  [CrabeLoader](https://github.com/LucasLhomme/DisneyInfinity-SplitScreenMods).
- La **creación de personaje** (avatar sólido de P2) de este repo.

Todo en Frida (script `scripts/dropin_full.py`). Direcciones RVA, ImageBase `0x400000`.

---

## La receta (3 piezas)

### 1. Join nativo (P2 real: mando + viewport + cámara + split)
El motor cablea cámara/viewport/mando SOLO cuando P2 es un jugador real. La forma de crearlo:
- `gamePlayers` singleton = `[[base + 0x69E3CF + 2]]`.
- `forceAllowed`: `[gamePlayers + 0x98] = 1` (limpia el rechazo de DropInCheck).
- `gameLoop` = `GameStandAloneLoop`, por heap-scan de su vtable (image `0x1D4418C`,
  runtime `base+0x194418C`) + verificar `+0x58`/`+0x308`/`+0x378` (`0x1D44180`/`0x1D44174`/`0x1D43F88`).
- **`FUN_00a9b020(gameLoop, pad=1)`** (RVA `0x69B020`, `__thiscall`) — encola el drop-in de P2,
  **saltándose los gates** de `OnDropInRequest` (`0x69E480`) que petan por un global nulo.
  → `secondPlayerId` pasa de -1 a 1, P2 real, el motor parte la pantalla y crea la 2ª cámara.

### 2. Cuerpo del avatar (evitar que expulsen a P2, hacerlo sólido)
El drop-in NO spawnea el cuerpo (el "reader wall" de CrabeLoader). Se fuerza así (hook `FUN_00e01890`
RVA `0xA01890`, `this`=mgr de avatares):
- Slot 1: `pA=[mgr+0xC]`; `pA+0x10 = SKU`, `pA+0x58 = 0x10000`; `mgr+0x83a = 1` (petición de unión);
  `mgr+0xb8c`/`playerCount=2`; `[mgr+0xcc]=1` + contexto del slot 1.
- Disparar SOLO ~45 frames y luego **CONGELAR** (`mgr+0x845 = 1`, `mgr+0x83a = 0`) → rompe el bucle
  de spawn y Mickey queda **sólido**. (Solidificar bit proxy en `de9dc0` RVA `0x9E9DC0`, slot 1, `+0x39 & ~2`.)

### 3. Mandos separados (ya lo hace el join)
El join ata cada jugador a su mando. El gestor de mandos = `DAT_02140194` (`[base+0x1D40194]`):
- `LockPlayerToController`: `[obj + playerIndex*4 + 0x44c] = controllerIndex`, `[obj+0x478]++`.
- `GetLockedControllerIndex(pi)` = `[obj + pi*4 + 0x44c]`.
- Tras el join se lee: `P0=0, P1=1` → mando 0 → Hulk, mando 1 → Mickey. **Separados.** ✓
  (Si hiciera falta forzarlo: `scripts/lock_controller.py`.)

---

## Cómo probarlo (Frida)
1. Instala Frida (ver `REQUISITOS.md`), 2 mandos conectados.
2. Abre el juego, entra a una **Toy Box** con tu personaje (P1), moviéndote.
3. `python scripts/dropin_full.py` — espera unos segundos: se une P2, se parte la pantalla y sale
   Mickey sólido. Cada mando mueve a su jugador.

## Scripts
- `dropin_full.py` — **el co-op completo** (join + personaje + separación de mandos).
- `dropin_join.py` — solo el join (útil para depurar / entender el método).
- `lock_controller.py` — atar mando N a jugador M (por si el lock no queda bien).
- `ctx_dump.py`, `disasm_handler.py` — utilidades de análisis en vivo.

## Limitaciones conocidas / siguiente
- **P2 no puede cambiar de muñeco** (la colección le sale bloqueada) — pendiente.
- El forzado del cuerpo es "a lo bruto" (bucle+congelar); se puede pulir.
- El `SKU` de P2 está fijo (Mickey `0xf431d`); se puede exponer un selector.

> Investigación de interoperabilidad. Sin código ni assets del juego.
