# 🎮 Disney Infinity 3.0 (PC/Steam) — Local Co-op & Play Set Research

> Investigación de ingeniería inversa (research WIP) sobre el port de PC de
> **Disney Infinity 3.0: Gold Edition**, para recuperar funciones presentes en consola
> pero no expuestas en PC. **Sin código del juego, sin assets, sin cracks.**

Dos objetivos:
1. **Pantalla partida / multijugador local (co-op).**
2. **Cualquier personaje jugable en cualquier Play Set** (saltarse el bloqueo de personaje cruzado).

Este repo es un **volcado de investigación** para que la comunidad de modding lo continúe:
scripts de instrumentación en vivo (Frida), la referencia técnica de offsets, el mapa completo del
problema y la hoja de ruta con próximos pasos concretos.

---

## 🚀 MOD INSTALABLE (DLL nativo) — ¡CO-OP EN MUNDOS + SELECCIÓN DE PERSONAJE!
Ya no es solo un script de investigación: hay un **mod instalable de verdad** en **[`mod/`](mod/)**.
Un único **proxy `bink2w32.dll`** (compilado con Zig, sin Python/Frida) que:

- **START en el mando 2** → el Jugador 2 se une: **pantalla partida, cámara propia, mando propio,
  cuerpo sólido** — en **Toy Box Y en Play Sets** (mundos de historia). ✅
- **LB+RB en el mando 2** → el Jugador 2 **cambia de personaje EN VIVO** (con su **modelo cargado**
  de verdad, no un placeholder). ✅
- Personaje inicial de P2 configurable por SKU en `coop_p2.txt` (lista completa de 111 personajes
  en [`mod/CHARACTERS_SKU.txt`](mod/CHARACTERS_SKU.txt)).

Instalación = copiar unos archivos + doble clic. Solo memoria del proceso: **no toca saves, red ni
logros**, reversible. Fuente en [`mod/src/coop.c`](mod/src/coop.c), guía en [`mod/README.md`](mod/README.md),
y la **receta técnica exacta para integrarlo en CrabeLoader** en
[`mod/RECIPE_FOR_CRABELOADER.md`](mod/RECIPE_FOR_CRABELOADER.md).

Piezas clave nuevas: drop-in `FUN_00a9b020(gameLoop,1)` (join) · materialización del cuerpo (hook
`e01890`) · **carga de modelo** vía `FUN_00b73060` (ruta `ActivateChanges`) · resolución sku→item
(`item+0xC8`=sku, `item+0xD0`=nombre).

---

## 🏆 CO-OP LOCAL DE 2 JUGADORES — FUNCIONANDO (probado en vivo, con foto)
**2 personajes sólidos (Hulk + Mickey) + 2 cámaras independientes + pantalla partida + MANDOS
SEPARADOS + estable.** Es el primer co-op local jugable conseguido en el port de PC de DI3.

Se logró **combinando dos proyectos complementarios**: el **join nativo** (mando+viewport+split) del
método de [CrabeLoader](https://github.com/LucasLhomme/DisneyInfinity-SplitScreenMods) + la
**creación de personaje** de este repo. Todo en un script Frida: **[`scripts/dropin_full.py`](scripts/dropin_full.py)**.

➡️ **Receta completa y direcciones en [`CO-OP_FUNCIONA.md`](CO-OP_FUNCIONA.md).**
➡️ Cómo encajan los dos proyectos en [`COLABORACION_CrabeLoader.md`](COLABORACION_CrabeLoader.md).
🙌 **Mérito compartido con [CrabeLoader](https://github.com/LucasLhomme/DisneyInfinity-SplitScreenMods) (LucasLhomme) — ver [`CREDITOS.md`](CREDITOS.md).**

### El camino (hitos previos, todos en vivo)
- Pantalla partida real (repunte de `PTR_FUN_020129f4`).
- Lectura del **mando 2** (`XInputGetState(1)`); offset de **posición del avatar** (`entidad+0x134`);
  **resolver handle→entidad** (`FUN_00492e20`); mapa cámara↔mando↔jugador. Ver [`AVANCES_JUGADOR2.md`](AVANCES_JUGADOR2.md).
- **La tecla final:** el join de P2 se hace llamando **directamente** al drop-in `FUN_00a9b020(gameLoop,1)`
  (saltando los gates que petan), y forzando el cuerpo del avatar (disparar + congelar).

## Estado / pendiente
- ✅ **Co-op funciona en mundos (Play Sets)**, no solo Toy Box.
- ✅ **P2 elige y cambia de personaje** (por SKU + botón LB+RB), con su **modelo cargado**.
- ⏳ El cambiador rota por **todos** los personajes (aún no filtra por franquicia del mundo).
- ⏳ Desbloquear el **menú/colección nativo** de P2 sigue siendo el muro del "perfil-invitado"
  (lo cubre `ForceUnlockData` de CrabeLoader → integración con Lucas).
- El cambio de personaje puede parpadear a P1 como "holograma" un instante (se auto-resuelve).

Detalle técnico completo en **[`HOJA_DE_RUTA.md`](HOJA_DE_RUTA.md)**, **[`CO-OP_FUNCIONA.md`](CO-OP_FUNCIONA.md)**
y **[`AVANCES_JUGADOR2.md`](AVANCES_JUGADOR2.md)**.

---

## 📁 Contenido
```
├── README.md                ← estás aquí
├── HOJA_DE_RUTA.md          ← ⭐ mapa técnico completo + próximos pasos
├── REFERENCIA_TECNICA.md    ← tabla de funciones/offsets por subsistema
├── REQUISITOS.md            ← cómo instalar Frida y ejecutar los scripts
├── LICENSE                  ← MIT (aplica a los scripts y docs de este repo)
└── scripts/                 ← instrumentación en vivo (Frida)
    ├── split_natural.py         ★ pantalla partida + sólido + cámara
    ├── split_test_simple.py       test aislado del split
    ├── join_and_split.py        ★ join natural (popup+Start) + split + cámara
    ├── any_char_playset.py      ★ intento de "cualquier personaje en cualquier Play Set"
    ├── natural_join.py            hace salir el popup nativo de unión
    ├── final_shot3.py             materializa al jugador 2 sin crash
    ├── final_shot4.py             jugador 2 jugable con el mando 2
    ├── dump_viewport.py           investigación de las cámaras
    └── trace_cameras.py           localizó el gap de cámara
```

## 🛠️ Uso rápido
Requiere **Python 3.12** + **Frida** (`pip install frida`) y el juego instalado. Con el juego
abierto en una Toy Box:
```bash
python scripts/split_natural.py
```
Los scripts hacen *hooks* en memoria del proceso en ejecución — **no modifican archivos del
juego**. Ver [`REQUISITOS.md`](REQUISITOS.md) para el detalle.

---

## ⚖️ Aviso legal / ético
- Proyecto **educativo, no comercial** de ingeniería inversa con fines de **interoperabilidad**,
  sobre una **copia legítima** del juego, para uso local.
- **No** incluye el ejecutable, ni assets, ni código del juego, ni evita ninguna protección/DRM.
- Los scripts únicamente leen/escriben memoria del proceso en ejecución para estudiar cómo
  funciona el motor. La **referencia técnica** solo lista direcciones y descripciones de
  comportamiento, no reproduce código del juego.
- Disney Infinity y sus marcas pertenecen a sus respectivos propietarios. Este proyecto no está
  afiliado ni respaldado por ellos.
- Úsalo bajo tu responsabilidad. Si algo debe retirarse, abre un issue.

## 🤝 Contribuir
Los próximos pasos concretos están en `HOJA_DE_RUTA.md`. Si avanzas cualquiera de los dos muros
(o encuentras el gate del menú de Play Sets), abre un PR o un issue. La investigación se hizo
en colaboración persona + Claude (Anthropic).

## 📄 Licencia
Código y documentación de **este repositorio** bajo licencia **MIT** (ver [`LICENSE`](LICENSE)).
No cubre ni concede derechos sobre nada perteneciente a Disney / el juego.
