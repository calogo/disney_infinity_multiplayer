# 📐 Referencia técnica — offsets y funciones clave

Mapa de las funciones y variables relevantes del motor de **Disney Infinity 3.0 (PC/Steam,
`DisneyInfinity3.exe`, 32-bit)** descubiertas durante la investigación.

Aquí solo hay **direcciones (RVA) y descripciones de comportamiento** — no código decompilado.
Con esto tienes los puntos exactos donde mirar/enganchar en tu propio Ghidra/Frida.

> **Convención:** ImageBase de Ghidra = `0x400000`.
> `RVA = dirección_Ghidra − 0x400000`. En runtime: `dirección = base_módulo + RVA`.

---

## 🖥️ Subsistema de PANTALLA PARTIDA

| Función / dato | RVA | Ghidra | Descripción |
|---|---|---|---|
| `FUN_00e01890` | `0xA01890` | `0x00e01890` | Update del game loop que corre cada frame; su `ecx` es el "manager" de jugadores. **Punto de enganche por frame.** |
| `PTR_FUN_020129f4` | `0x1C129F4` | `0x020129f4` | **EL CANDADO.** Puntero al cálculo del modo de split. En PC apunta a un stub que da 0. Repuntarlo a un callback que devuelva el modo (2=vertical) activa el split por la vía natural. |
| `FUN_00969b60` | `0x569B60` | `0x00969b60` | Stub `return 0` **compartido** (usado como "null" en muchos vtables). **No parchear sus bytes** o crashea a otros llamadores. |
| `FUN_018b0c60` | `0x14B0C60` | `0x018b0c60` | Compara modo calculado vs actual; si cambió, aplica el modo y **dispara los eventos** `SplitScreenChange` y `GamePlaySplitScreenChange` (que reconfiguran el render). |
| `FUN_006663e0` | `0x2663E0` | `0x006663e0` | Aplica el modo de split: fija el modo efectivo, recalcula regiones y nº de viewports. |
| `FUN_0065e970` | `0x25E970` | `0x0065e970` | Recalcula las regiones de viewport según el modo. |
| `FUN_00aad820` | `0x6AD820` | `0x00aad820` | Copia las regiones al array de viewports y fija su número. |
| `FUN_0044a990` | `0x4A990` | `0x0044a990` | Define una región de viewport (x,y,w,h). |
| `_DAT_020117a8` | `0x1C117A8` | `0x020117a8` | Modo de split efectivo (0=full, 1=horizontal, 2=vertical, 9=combinado Toy Box…). |
| `DAT_020117b0` | `0x1C117B0` | `0x020117b0` | Modo de split para el HUD. |
| `DAT_02059d60` | `0x1C59D60` | `0x02059d60` | Número de viewports activos. |
| `DAT_02213748` | `0x1E13748` | `0x02213748` | Array de regiones de viewport. |

---

## 🎥 Subsistema de CÁMARA

| Función / dato | RVA | Ghidra | Descripción |
|---|---|---|---|
| `DAT_0228e8e4` | `0x1E8E8E4` | `0x0228e8e4` | Cabeza de la lista enlazada de cámaras (`next` en `+0x1c0`). Hay 2 cámaras y son la misma clase. |
| `FUN_018add10` | `0x14ADD10` | `0x018add10` | Dispatcher del update por-cámara. Corre el update solo si `(char)cam[0xB0] != 0` (gate volátil). |
| `FUN_016de4d0` | `0x16DE4D0` | `0x016de4d0` | Método `update` de la cámara (vtable+0xc). |
| `FUN_018b9e40` | `0x14B9E40` | `0x018b9e40` | Sub del update. Contiene el seguimiento-por-handle (lee `cam+0x158`), **gated por `cam+0x1b4`**. |
| `FUN_016dc1d0` | `0x12DC1D0` | `0x016dc1d0` | Sub del update que posiciona la vista leyendo del gestor de cámaras. |
| `FUN_018adcf0` | `0x14ADCF0` | `0x018adcf0` | **Gestor de cámaras** (singleton). Eye en `+0x3c..0x44`, target/look-at en `+0x48..0x50`. Es de aquí de donde el render saca la vista. |
| `FUN_018bc350` | `0x14BC350` | `0x018bc350` | Activar cámara (real). |
| `FUN_018bca50` | `0x14BCA50` | `0x018bca50` | Wrapper de activar cámara. |
| `FUN_013a3d00` | `0xFA3D00` | `0x013a3d00` | Asigna cámaras a viewports (recorre la lista de cámaras). |

**Campos relevantes de la estructura de cámara:**
`+0xB0` gate de update (byte bajo) · `+0xc0..0x138` matriz de vista (el render NO la usa directamente) ·
`+0x158/0x15c` handle del avatar a seguir · `+0x1b4` habilita el seguimiento por handle ·
`+0x1c0` puntero a la cámara siguiente.

---

## 🧍 Subsistema de SPAWN / UNIÓN del jugador 2

| Función / dato | RVA | Ghidra | Descripción |
|---|---|---|---|
| `FUN_00df3410` | `0x9F3410` | `0x00df3410` | Evento de figura/tag; se dispara al pulsar Start (o al procesar la solicitud de unión). |
| `FUN_00dd0d20` | `0x9D0D20` | `0x00dd0d20` | Añadir jugador / mostrar el popup de unión. |
| `FUN_00df21e0` | `0x9F21E0` | `0x00df21e0` | Máquina de estados de la unión. |
| `FUN_00dd19e0` | `0x9D19E0` | `0x00dd19e0` | Crea la entidad del avatar. |
| `FUN_00aa36f0` | `0x6A36F0` | `0x00aa36f0` | Finaliza la creación del avatar. |
| `FUN_00a9fd00` | `0x69FD00` | `0x00a9fd00` | "Swap" del avatar; expone el handle empaquetado del nuevo avatar. |
| `FUN_00de9dc0` | `0x9E9DC0` | `0x00de9dc0` | Materializa el avatar en estado SÓLIDO. |
| `DAT_0220191c` | `0x1E0191C` | `0x0220191c` | Flag del candado "1 jugador"; forzarlo a 1 desbloquea el flujo de unión / popup. |
| `DAT_0225f540` | `0x1E5F540` | `0x0225f540` | Contexto/contador global. `+0x94` = nº de jugadores; `+0x108` = array de contextos de jugador. |

**Campos relevantes del "manager"** (`ecx` de `FUN_00e01890`):
`+0x08` pB · `+0x0c` pA · `+0x60/+0x64` índice de mando de jugador 0 / 1 · `+0x83a` solicitud de
unión (=1 dispara el popup) · `+0x845` =1 solidifica el slot (skip) · `+0xcc` actor-id del slot 1.

---

## 🎭 Subsistema de COMPATIBILIDAD personaje ↔ Play Set

| Función / dato | RVA | Ghidra | Descripción |
|---|---|---|---|
| `FUN_00ddae30` | `0x9DAE30` | `0x00ddae30` | Validación compat. personaje-playset (1=ok, 0=bloqueado + errCode). **Ojo:** es la validación in-game de figuras/adventures, **NO** el gate de la selección de Play Set en el menú. |
| `FUN_00dfe850` | `0x9FE850` | `0x00dfe850` | Genera los diálogos "CrossOverNotAllowed" / "CrossOverLocked". Es el diálogo, no el gate. |
| `FUN_00dd15e0` | `0x9D15E0` | `0x00dd15e0` | Cómputo del resultado de crossover (candidato a revisar). |
| `FUN_013a40a0` | `0xFA40A0` | `0x013a40a0` | Gate de "split-screen permitido" en la zona. |

**Pendiente:** localizar el gate real del menú de Play Sets (no es `ddae30`). Candidatos: las
funciones-filtro del menú. Strings útiles para buscar en el binario: `UIPlaysetFilter`,
`Scn_Filter_*`, `CrossOver*`, `SplitScreenAllowed`.

---

*Toda esta información se obtuvo con Ghidra (estático) + Frida (dinámico) sobre una copia legítima
del juego, con fines de investigación de interoperabilidad. Ver `HOJA_DE_RUTA.md` para el mapa
completo del razonamiento y los próximos pasos.*
