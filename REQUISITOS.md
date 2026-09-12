# 🛠️ Requisitos y cómo ejecutar los scripts

## Necesitas
- **Disney Infinity 3.0: Gold Edition (Steam)** instalado, versión PC (`DisneyInfinity3.exe`, 32-bit).
- **Python 3.12** (x86/32-bit recomendado, para casar con el proceso de 32 bits — aunque Frida
  suele funcionar desde Python x64 también).
- **Frida:**
  ```
  pip install frida
  ```
- (Opcional, para el análisis estático) **Ghidra 11+** con el `.exe` importado y analizado.

> En el equipo original se usó un **Python portable** con Frida ya instalado, dentro de la carpeta
> de herramientas del proyecto. Aquí NO se incluye (pesa mucho para Discord). Instala Frida tú con
> el `pip install` de arriba.

## Cómo lanzar un script
1. Abre el juego y llega al punto que pide el script:
   - `split_natural.py`, `split_test_simple.py`, `final_shot3/4.py`, `natural_join.py`,
     `join_and_split.py`, `dump_viewport.py`, `trace_cameras.py` → **dentro de una Toy Box**.
   - `any_char_playset.py` → en el **menú de selección de Play Set**.
2. Con el juego ya abierto y estable, ejecuta desde una terminal:
   ```
   python scripts\split_natural.py
   ```
3. Mira la **consola de Python** (te dice qué está haciendo y qué mirar) **y la pantalla del juego**.
4. Para parar: `Ctrl+C` en la terminal.

## Notas importantes
- Los scripts **no modifican archivos del juego**: hacen *hooks* en la memoria del proceso en
  ejecución. Al parar el script, el efecto desaparece.
- Varios scripts (los que activan el split) **repuntan un puntero a un callback de Frida**. Si
  paras el script en caliente, ese puntero queda colgando y **el juego se cierra**. Es normal:
  reabre el juego limpio para el siguiente intento.
- Si un script dice "no encuentra el proceso", asegúrate de que el juego está abierto y de que el
  nombre del proceso es `DisneyInfinity3.exe` (algunos scripts lo buscan por nombre).
- Todas las direcciones de memoria están calculadas para una build concreta del exe. Si tu build
  difiere, puede que haya que reajustar los RVA (ver `HOJA_DE_RUTA.md`).

## El script estrella para empezar
```
python scripts\split_natural.py
```
Estando en una Toy Box: materializa al jugador 2, lo solidifica, **parte la pantalla** y aplica
los arreglos de cámara conocidos. Es el que integra todo lo conseguido en el Objetivo 1.
