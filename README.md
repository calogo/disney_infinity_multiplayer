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

## ✅ Conseguido (probado en vivo)
- **La pantalla se PARTE de verdad** — 2 viewports, línea divisoria, estable, sin crash.
- **Segundo personaje materializado, SÓLIDO y (en su momento) jugable con el mando 2.**
- **Popup nativo de "pulsa Start para unirte"** reproducido en PC.
- **Mapa completo** de cómo se relacionan cámara ↔ mando ↔ jugador local.

## ❌ Los dos muros (documentados)
1. **Split-screen jugable estable:** el binding del *mando físico → jugador 2* depende de la
   confirmación de la **figura física en el portal**, que en PC no existe. Ese mismo binding da
   objetivo a la 2ª cámara → cámara y mando fallan por la misma raíz.
2. **Cualquier personaje en cualquier Play Set:** la función de compat. que se probó no es el gate
   del menú. Falta localizar el filtro real (candidatos anotados). Probablemente más alcanzable.

Detalle completo y próximos pasos en **[`HOJA_DE_RUTA.md`](HOJA_DE_RUTA.md)**.

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
