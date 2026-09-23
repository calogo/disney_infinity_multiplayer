# 🙌 Créditos

Este co-op funcional es fruto de **dos proyectos complementarios**. El mérito es compartido.

## CrabeLoader / DisneyInfinity-SplitScreenMods
- **[LucasLhomme](https://github.com/LucasLhomme)** — autor de
  **[CrabeLoader](https://github.com/LucasLhomme/CrabeLoader)** y de
  **[DisneyInfinity-SplitScreenMods](https://github.com/LucasLhomme/DisneyInfinity-SplitScreenMods)**.
  Suyo es el **join nativo del Jugador 2** (mando + viewport + pantalla partida): el método
  `OnDropInRequest` / `FUN_00a9b020`, `forceAllowed`, la localización del `GameStandAloneLoop`, el
  `LockPlayerToController`, y toda la investigación del drop-in documentada en su `docs/splitscreen.md`.
  **Sin su trabajo, la mitad "join" de este co-op no existiría.**
- **[Nyatsukii](https://github.com/Nyatsukii)** — colaborador/a de ese proyecto.

## Este repo
- Investigación de la **creación/materialización del personaje de P2** (avatar sólido), el offset de
  posición del avatar, el resolver handle→entidad, y el ensamblaje final que combina ambas mitades
  (`scripts/dropin_full.py`).

## Cómo encajan
Ellos tenían el join pero el 2º personaje no spawneaba (su muro documentado). Este repo tenía el
personaje pero no el join. **Juntando las dos mitades salió el co-op jugable.** Detalle en
[`CO-OP_FUNCIONA.md`](CO-OP_FUNCIONA.md) y [`COLABORACION_CrabeLoader.md`](COLABORACION_CrabeLoader.md).

Ambos proyectos son investigación de interoperabilidad, sin código ni assets del juego.
Licencias respectivas: este repo MIT; CrabeLoader y su mod, GPLv3.
