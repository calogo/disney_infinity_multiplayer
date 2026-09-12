# 🗺️ Hoja de Ruta — Disney Infinity 3.0 PC

Mapa técnico de los dos objetivos: qué está resuelto, dónde está el muro, y los próximos pasos
concretos. Para el detalle exhaustivo sesión por sesión, ver `HANDOFF_TECNICO.md`.

> **Convención de direcciones:** Ghidra usa ImageBase `0x400000`.
> `RVA = dirección_Ghidra − 0x400000`. En runtime: `dirección = base_módulo + RVA`.

---

# 🎯 OBJETIVO 1 — Pantalla partida / co-op local

## ✅ RESUELTO: la pantalla se parte de verdad

**El candado de PC:** el game loop `FUN_018b0c60` calcula el modo de split leyendo un puntero
`PTR_FUN_020129f4`. En PC ese puntero da **0** (un stub) → siempre "sin split". En consola daría
el modo según nº de jugadores.

**La solución (funciona, `split_natural.py`):** repuntar el puntero `PTR_FUN_020129f4`
(en `base + 0x1C129F4`) a un `NativeCallback` que devuelve el modo deseado (2 = vertical).
Con el modo calculado ≠ 0, `FUN_018b0c60` dispara **toda la cadena natural** de eventos:
`FUN_006663e0` (fija viewports) + evento `"SplitScreenChange"` + evento
`"GamePlaySplitScreenChange"` → los viewport controllers reconfiguran el render **de verdad**.

**Resultado en vivo:** `modoSplit=2, numViewports=2`, línea divisoria real, 2 viewports, estable,
sin crash. Confirmado con foto.

### ⚠️ Errores que costaron sesiones (NO repetir)
- ❌ Escribir la variable de modo `_DAT_020117a8 = 2` a mano **no basta**: se salta los eventos,
  el render no reconfigura.
- ❌ Parchear los **bytes** del stub `FUN_00969b60` (`return 0`) a `mov eax,2` **CRASHEA**: es un
  thunk **compartido** usado como "null" en muchos vtables. Otros llamadores hacen `deref(2)` →
  crash `read@0x2`. Hay que repuntar **solo** el puntero dedicado, no el stub.
- ❌ Aritmética: `0x020129f4 − 0x400000 = 0x1C129F4` (¡no `0x16129F4`!).

## ✅ RESUELTO: segundo personaje sólido, sin bucle
- **Materializar:** en el hook de `FUN_00e01890`, escribir los campos del "manager" (`mgr` = ecx)
  para que el juego cree la entidad del jugador 2 (SKU en `pA+0x10`, `mgr+0x83a=1`, `mgr+0xcc=1`,
  contexto selectivo `ctx1+0x10=1`...). Ver `final_shot3.py` / `split_natural.py`.
- **Sólido:** `mgr+0x845=1` (skip slot) tras materializar → el avatar se solidifica y deja de
  re-crearse en bucle. (El bit "proxy" `avatar+0x39 & 2` NO era la causa del fantasma.)

## ❌ EL MURO: la cámara y el mando del jugador 2

Mapa completo (todo confirmado en vivo):
- La lista de cámaras está en `base + 0x1E8E8E4` (`DAT_0228e8e4`, `next` en `+0x1c0`). **Hay 2
  cámaras** y son **la MISMA clase** (misma vtable). cam1 NO es un placeholder.
- El update por-cámara es `FUN_018add10`: `if ((char)cam[0xB0]!=0) cam->vtable[0xc]()`.
  cam1 tiene `[0xB0]` con byte bajo 0 → **su update se salta** → matriz identidad → mira al cielo.
  Forzando `cam1[0xB0] |= 1`, el update de cam1 **sí corre** (confirmado).
- **PERO** aun corriendo el update, cam1 sigue en el cielo, y **el render NO lee `cam+0xc0`**
  (copiar la matriz de cam0 no cambia nada). La vista real la produce el **gestor de cámaras**
  `FUN_018adcf0` (target/look-at en `mgr+0x48/0x4c/0x50`), que está **vacío** para cam1.
- Ese target lo rellena el **sistema de jugador-local**. El **mando 2 tampoco se asigna** al
  jugador 2. → **Cámara y mando son la MISMA pieza**: ambos cuelgan de un "jugador local"
  completo, que nace cuando se pulsa Start en el popup con una **figura física** confirmada.
- En PC no hay figura ni portal, así que ese flujo natural **no se completa**. Forzar el popup
  con `mgr+0x83a=1` auto-procesa la unión (sin esperar Start real) y asigna solo **índices**
  (`mgr+0x64=1`), pero **no bindea el dispositivo físico** del mando 2.

### 👉 Próximos pasos (Objetivo 1)
Esta es la razón de fondo por la que el port de PC no trae splitscreen. Dos caminos, ambos grandes:
1. **Emular el hardware de figura/portal** (Infinity Base USB) para que el juego "vea" una figura
   del jugador 2 y complete el flujo nativo → bindearía mando + cámara solos. *(el más "correcto")*
2. **Interceptar el enrutado de input a bajo nivel** (XInput/pad → jugador) para forzar que el
   mando 2 controle a Mickey, y sintetizar la cámara aparte (escribir el target en
   `FUN_018adcf0()+0x48..0x50` en el momento correcto del frame). *(hack, más frágil)*

### 📌 Tabla de direcciones clave (Objetivo 1)
| Símbolo (Ghidra) | RVA | Qué es |
|---|---|---|
| `FUN_00e01890` | `0xA01890` | update estable del game loop (punto de enganche por frame; `ecx`=manager) |
| `PTR_FUN_020129f4` | `0x1C129F4` | **puntero del cálculo de modo split (EL CANDADO)** — repuntar aquí |
| `FUN_00969b60` | `0x569B60` | stub `return 0` COMPARTIDO — **NO tocar sus bytes** |
| `FUN_018b0c60` | `0x14B0C60` | dispara `SplitScreenChange` / `GamePlaySplitScreenChange` |
| `FUN_006663e0` | `0x2663E0` | aplica el modo split (fija `numViewports`, regiones) |
| `_DAT_020117a8` | `0x1C117A8` | modo split efectivo |
| `DAT_02059d60` | `0x1C59D60` | nº de viewports |
| `DAT_0228e8e4` | `0x1E8E8E4` | cabeza de la lista de cámaras (`next` en `+0x1c0`) |
| `FUN_018add10` | `0x14ADD10` | dispatcher del update por-cámara (gate `cam[0xB0]`) |
| `FUN_016de4d0` | `0x16DE4D0` | método update de la cámara (vtable+0xc) |
| `FUN_018adcf0` | `0x14ADCF0` | **gestor de cámaras** (eye `+0x3c..0x44`, target `+0x48..0x50`) |
| `FUN_00e9dc0` (de9dc0) | `0x9E9DC0` | materializa el avatar (sólido) |
| `mgr+0x845` | — | =1 solidifica el slot (skip); =0 lo mantiene en creación |
| `mgr+0x83a` | — | =1 solicita la unión (dispara el popup / el flujo de join) |
| `mgr+0xcc` | — | actor-id del slot 1 |
| `mgr+0x60 / +0x64` | — | índice de mando de jugador 0 / jugador 1 |

---

# 🎯 OBJETIVO 2 — Cualquier personaje en cualquier Play Set

## Estado: 1er intento fallido, pero acotado

**Idea:** existe una validación de compatibilidad personaje↔playset que devuelve permitido/
bloqueado y produce los diálogos `"DialogType_CrossOverNotAllowed"` / `"CrossOverLocked"`.

**Lo probado (`any_char_playset.py`):** hookear `FUN_00ddae30` (RVA `0x9DAE30`) — devuelve
1=compatible / 0=bloqueado y pone un `errCode` (2=CrossOver, 3=Locked, 7=SKUOnly...). Se forzó
retval=1 + errCode=0.

**Resultado:** ❌ **NO funcionó** — al intentar entrar a un Play Set con un personaje "no
permitido", `FUN_00ddae30` **ni se llamó** (`llamadas=0`). Así que **ese no es el gate del menú**
(probablemente `ddae30` valida figuras físicas / adventures in-game, no la selección de Play Set).

### 👉 Próximos pasos (Objetivo 2)
Localizar el **gate real de la selección de Play Set en el menú**. Método: hookear en vivo las
funciones-filtro mientras se navega el menú con un personaje cruzado, ver cuál se dispara y decide
el bloqueo. Candidatos (con análisis previo en el HANDOFF): `char_filter`, `filter_funcs`,
`playsetfilter_users`, `playset_char_refs`, y `FUN_00dd15e0` (cómputo del crossover, lo llama
`ddae30`). Strings útiles para buscar: `"UIPlaysetFilter"`, `"Scn_Filter_*"`, `"CrossOver*"`.
**NO repetir `ddae30`** (confirmado que no aplica al menú).

### 📌 Direcciones clave (Objetivo 2)
| Símbolo | RVA | Qué es |
|---|---|---|
| `FUN_00ddae30` | `0x9DAE30` | validación compat. (in-game; **no** el gate del menú) |
| `FUN_00dfe850` | `0x9FE850` | genera los diálogos "CrossOverNotAllowed" (es el diálogo, no el gate) |
| `FUN_00dd15e0` | `0x9D15E0` | cómputo del crossover (candidato a revisar) |

---

## 🧰 Entorno / metodología (reutilizable)
- **Ghidra** para el análisis estático (proyecto con el .exe ya analizado).
- **Frida** para instrumentación en caliente: `Interceptor.attach` (onEnter/onLeave),
  `NativeFunction`, `NativeCallback`, `Memory.read/write`, `Process.setExceptionHandler`.
- Patrón de trabajo: hookear `FUN_00e01890` (corre cada frame, da el `manager` en `ecx`),
  escribir/leer campos, y usar `send()` para loguear a la consola de Python.
- **Cuidado:** repuntar un puntero a un `NativeCallback` de Frida y luego parar el script deja el
  puntero colgando → el juego crashea. En un mod DLL final esto no pasa (el código vive con el
  proceso). Para pruebas: parar script = reabrir juego.

## 🎁 Meta final del mod (cuando se cierre)
DLL/ASI cargado con un loader genérico: parche **mínimo, reversible, sin tocar
guardado/red/logros**, que verifique versión/hash del exe, e instalación **simple** (copiar
archivos). Toda la investigación apunta a eso.
