# 🕹️ Avances Jugador 2 — enfoque "marioneta" (títere)

Sesión larga centrada en el **co-op local**, con un enfoque nuevo del usuario: en vez de pedirle al
juego que "una" al Jugador 2 (bloqueado en todas las capas del *join*), **crear el avatar de P2 y
manejarlo desde fuera** (leer el mando 2 + posicionar avatar y cámara). Varios avances concretos y
un muro final bien acotado.

> Convención de direcciones: Ghidra ImageBase `0x400000`. `RVA = Ghidra − 0x400000`.
> Runtime: `dirección = base_módulo + RVA`. Todo verificado en vivo con Frida.

---

## ✅ Conseguido en esta fase (visible en pantalla)

1. **Pantalla partida + Jugador 2 sólido a la vez.** Mickey (P2) materializado SÓLIDO, en el mundo,
   con su marcador "2", junto a P1 (Hulk), con la pantalla partida en 2 viewports.
   Scripts: `split_natural.py` (materializa + parte) y `puppet_p2.py` (materializa el títere).

2. **Se lee el MANDO 2 entero desde el inyector.** `XInputGetState` está en `XINPUT9_1_0.dll`.
   Llamando `XInputGetState(1, buf)` leemos stick (LX/LY en +10/+12, S16) y botones (+4, U16) del
   2º mando. El juego además **consulta el índice 1** (ve el mando 2), solo que no lo enruta.
   Script: `xinput_probe.py`. → La fuente de input del títere está resuelta.

3. **Localizado el offset de la POSICIÓN del avatar** (el gran desbloqueo).
   Método: mover a P1 con el mando 1 y ver qué campos de su entidad cambian (`change_finder.py`,
   `dump_ent.py`). Bloque de transform dentro de la entidad del avatar:
   - `entidad + 0x128/0x12c/0x130` = **dirección/mirada** (vector unitario).
   - `entidad + 0x134/0x138/0x13c` = **POSICIÓN (X, Y, Z)** — la Y (+0x138) no cambia al andar
     (altura del suelo), X/Z sí. Confirmado.
   - `entidad + ~0x160..0x16c` = **velocidad** (se va a 0 al parar).
   - (El `+0x2c` de scripts previos era incorrecto; el bueno es **+0x134**.)

4. **Resolver de handle → entidad descifrado.** `FUN_00492e20` (RVA `0x92E20`) es `__thiscall`:
   `ecx` = tabla de handles (global), stack `param2`=out, `param3`=&handle; devuelve el slot;
   `entidad = [ret+8]`. Forma fiable de obtener la entidad de cualquier avatar: **hookear ese
   resolver** y filtrar por handle (o por tipo `0x30xxxxxx`). Script: `resolve_pos.py`.

5. **La 2ª cámara SÍ renderiza el mundo.** Con el split activo, la cámara derecha muestra la escena
   (se vio a P1 desde ella). El mecanismo de render del 2º viewport funciona.

---

## ⛔ El muro final (bien entendido): el "ojo" de la 2ª cámara

Objetivo: que la cámara derecha **enfoque a Mickey**. Estado:

- Las 2 cámaras se distinguen por `cam+0x1b4`: cam0 (izq, Hulk) `=0`, cam1 (der, Mickey) `=1`,
  con `cam+0x158` = handle del avatar a seguir. Inspección: `cam_inspect.py`.
- El **follow por handle** del juego (`FUN_018b9e40`, gated por `cam+0x1b4`) lee la posición del
  avatar en **`entidad+0x268`** (avatar) o `+0x2c`. Poblamos `+0x268` con la posición real (+0x134)
  y aún así cam1 no encuadra → el follow fija el **target** pero el **ojo** (eye) de cam1 lo pone
  otra cosa. Scripts: `cam_pos_feed.py`, `cam_follow_inject.py`.
- **Escribir la matriz de vista de cam1 directamente NO sirve:** el juego la **recalcula cada frame**
  desde su ojo/target internos y pisa nuestra escritura (probado con copia de cam0 y con look-at
  propio). Confirmado en vivo.

**Conclusión:** para encuadrar cam1 hay que controlar la **fuente** de su vista (ojo/target), no la
matriz final. Candidatos: el gestor de cámara `FUN_018adcf0` (eye `+0x3c`, target `+0x48`) y el
update por-cámara `FUN_016dc1d0` (que aún no dispara para cam1). Es el siguiente paso concreto.

---

## Tabla de direcciones nuevas (resumen)

| Qué | Dónde |
|---|---|
| Posición del avatar (X,Y,Z) | `entidad + 0x134 / 0x138 / 0x13c` |
| Dirección/mirada del avatar | `entidad + 0x128 / 0x12c / 0x130` |
| Posición que lee el follow de cámara | `entidad + 0x268` (avatar) o `+0x2c` |
| Resolver handle→slot (`[ret+8]`=entidad) | `FUN_00492e20` RVA `0x92E20` (`__thiscall`, ecx=tabla) |
| Follow de cámara por handle | `FUN_018b9e40` (gated por `cam+0x1b4`, handle en `cam+0x158`) |
| Flag/handle de la 2ª cámara | `cam+0x1b4` (1=follow on), `cam+0x158` (handle) |
| Leer mando 2 | `XInputGetState(1, buf)` de `XINPUT9_1_0.dll` |

## Próximo paso
Hacer que la inyección de eye/target alcance a **cam1** (via `FUN_016dc1d0` o el gestor
`FUN_018adcf0`), alimentándole `eye = Mickey + offset` y `target = Mickey`. Con eso, la cámara
derecha enfoca al títere. El movimiento con el mando 2 ya es directo (escribir `entidad+0x134`).
