# 🤝 Colaboración: CrabeLoader Splitscreen (proyecto complementario)

Otro proyecto ataca el **mismo objetivo** (co-op local en DI3 PC) desde el ángulo opuesto:

**[LucasLhomme/DisneyInfinity-SplitScreenMods](https://github.com/LucasLhomme/DisneyInfinity-SplitScreenMods)**
(mod de [CrabeLoader](https://github.com/LucasLhomme/CrabeLoader), en Lua).

## Por qué encajan (piezas espejo)

| Pieza | CrabeLoader (ellos) | Este repo (Frida, nosotros) |
|---|---|---|
| **Join de P2**: mando + viewport + pantalla partida | ✅ funciona | ❌ (era nuestro muro) |
| **Personaje sólido de P2 en el mundo** | ❌ (su muro) | ✅ Mickey sólido |

**Y lo clave:** su muro documentado es *"el lector nunca gana una 2ª figura, así que el avatar de P2
nunca se spawnea"* — que es **exactamente** lo que este repo resuelve forzando el lector/manager
(`mgr+0xb8c=1` + el bucle de creación de `FUN_00e01890` → `dd19e0`/`0x9D19E0` con la SKU del slot 1).

## El JOIN de ellos (direcciones, RVA base 0x400000) — nuestra pieza que faltaba

De su `api/45_dropin.lua`:
- **`gamePlayers`** singleton = `[[base + 0x69E3CF + 2]]` (deref del operando de un `mov`).
- **`forceAllowed`**: escribir `[gamePlayers + 0x98] = 1` (limpia bit de rechazo de `DropInCheck`).
- **`gameLoop`** = `GameStandAloneLoop`, localizado por heap-scan de su vtable `image 0x1D4418C`
  (runtime `base+0x194418C`) + verificar 3 vtables más en `+0x58`/`+0x308`/`+0x378`
  (`0x1D44180`/`0x1D44174`/`0x1D43F88`). Confirmado localizable también desde Frida.
- **`OnDropInRequest`** = `callThis1(base + 0x69E480, gameLoop, pad=1)` ← **el join**.
  - ⚠️ **Requiere STAGING antes**: `LockPlayerToController(1, pad)` + `Players_ForceAvatar/ChangeAvatar(1, sku)`.
    Sin ese staging, `OnDropInRequest` peta en un global nulo (verificado: fault leyendo `[0xc]`).
- `secondPlayerId` = `callThis0(base+0xF80740, players)` (primary) → `callThis1(base+0xF806E0, players, primary)` (second).

## El PERSONAJE nuestro (lo que a ellos les falta)

Ver `HOJA_DE_RUTA.md` / `AVANCES_JUGADOR2.md`. Resumen: forzar el 2º slot del manager de creación
(`mgr+0xb8c=1`, SKU del slot 1 en `pA+0x10`, dejar correr `FUN_00e01890` que llama a `dd19e0`), y
solidificar tras materializar (`mgr+0x845=1`). Resultado: avatar de P2 **sólido** en el mundo.
Además tenemos localizado el **offset de posición del avatar** (`entidad+0x134`) y el **resolver
handle→entidad** (`FUN_00492e20`, `__thiscall`, `[ret+8]`=entidad).

## Divergencia de herramientas
- Ellos: **CrabeLoader** (cargador con puente Lua) → llaman *natives* del juego (`LockPlayerToController`,
  `Players_ForceAvatar`...) limpiamente.
- Nosotros: **Frida** (memoria/funciones crudas). Replicar su staging en Frida requiere localizar las
  implementaciones C de esos natives (o instalar CrabeLoader y añadir nuestro forzado de lector a su mod).

## Camino a un co-op funcional (propuesta)
1. **Combinar en CrabeLoader:** su loader ya da el join+cámara+mando+split. Añadir a su `splitscreen.lua`
   nuestro **forzado de lector** (equivalente Lua/nativo de `mgr+0xb8c` + `dd19e0` para el slot 1) para
   spawnear el cuerpo de P2 → su muro cae. Es la vía más rápida a co-op jugable.
2. O **compartir este hallazgo** con su repo (issue/PR): están trabajando justo en eso y su
   infraestructura (loader + puente Lua + breakpoints) es ideal para integrarlo.

> Ambos proyectos son investigación de interoperabilidad, sin código ni assets del juego.
