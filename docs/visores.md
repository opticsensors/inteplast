# Visores de los datos crudos — dónde está el código

> 📁 **El código vive en este mismo repo**, en `data-explorer/` (raíz del repo). No en
> `scripts/`, que es el de build y test del template FastAPI.
>
> ```
> C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\repos\inteplast\data-explorer
> ```
>
> Este documento es el resumen: qué hay allí, qué hace y qué decisiones lleva dentro.
> La documentación de uso completa está en el [`README.md` de esa carpeta](../data-explorer/README.md).
>
> 🔴 Los **datos** que lee sí están fuera del repo, en
> `…\Escritorio\proyectos\11. inteplast\Exemples`.

---

## Qué hay

| Fichero | Qué hace |
|---|---|
| **`ver_todo.py`** | **Punto de entrada.** Ejecuta los tres visores y genera `out/index.html`, la pantalla donde se elige entre CSV, TXT y PDF |
| `ver_csv.py` | Los **16 CSV de cavidad** → árbol + 24 páginas |
| `ver_txt.py` | Las **40 nubes de puntos** `.txt` → árbol + 44 páginas |
| `ver_pdf.py` | Las **144 gráficas de contorno** en PDF → árbol + 148 páginas + 144 PNG |
| `README.md` | Uso, opciones y las trampas de los datos que los scripts ya resuelven |
| `out/` | Lo generado (~42 MB). **Ignorado en git**, se rehace en un par de minutos |

```
out/index.html            ← SE ABRE ESTO: elegir entre los tres
 ├── csv-3212.html        las cotas medidas y comparadas contra el plano
 ├── txt-3212.html        las nubes de puntos en bruto
 └── pdf-3212.html        el perfil interior contra el contorno teórico
```

## Cómo se ejecutan

🔴 **Python no está en el PATH** — el `python.exe` de la consola es el stub de la Microsoft Store
y falla. Hay que llamarlo por ruta absoluta:

```powershell
$py = "C:\Users\eduard.almar\AppData\Local\Programs\Python\Python311\python.exe"
$s  = "C:\Users\eduard.almar\OneDrive - EURECAT\Escritorio\repos\inteplast\data-explorer"

& $py "$s\ver_todo.py"                 # genera los tres y abre la pantalla inicial
& $py "$s\ver_todo.py" --solo pdf      # regenera solo uno
& $py "$s\ver_csv.py" --corregir-signo # invierte el error de signo de B2/B4
& $py "$s\ver_txt.py" --familia nous --muestreo 01
& $py "$s\ver_pdf.py" --zoom 2.0       # render de los PDF más grande
```

Python 3.11.8 con `pandas`, `numpy` y `plotly` ya instalados. → [CLAUDE.md](../CLAUDE.md)

⚠️ `ver_txt.py` **hidrata ficheros de OneDrive** (36 de los 40 `.txt` son placeholders, ~22 MB).
La primera pasada tarda un par de minutos.

---

## Qué muestran

**`ver_csv.py`** — árbol con una carpeta por muestreo (`intern.01`, `.03`, `.05`, `.08`) y sus 4
cavidades, más dos carpetas de comparativas al final:

1. **Un fichero medido**: una barra por característica, en el orden real del fichero. El eje X va
   en **fracción de la tolerancia consumida** (`0` = nominal, `±1` = límite) para poder comparar
   en el mismo gráfico cotas de ±0,5 mm y de ±0,02 mm. El hover da los mm reales.
2. **Comparar las cavidades entre sí** (una página por muestreo): separa un problema del molde
   entero de uno de una sola cavidad.
3. **Comparar los muestreos entre sí** (una página por cavidad): heatmap 211 cotas × 4 muestreos.
   Una fila que pasa de roja a verde es **un retoque que funcionó**.

**`ver_txt.py`** — árbol de dos niveles (muestreo → cavidad → los 3 ficheros de esa cavidad).
Cada página trae la nube 3D girable y la vista en planta, con el nº de puntos, el bounding box y
los niveles de altura detectados. Al final, los puntos objetivo de cada muestreo superpuestos.

**`ver_pdf.py`** — árbol de dos niveles (muestreo → cavidad → las 12 gráficas). Cada página lleva
los 6 números extraídos, una barra que sitúa la desviación respecto a la banda de tolerancia, y
**la página del PDF renderizada** para juzgar la gráfica original al lado del dato. Al final, la
evolución del contorno por cavidad a lo largo de los muestreos.

---

## Decisiones que llevan dentro (y por qué)

- **Los `totes.csv` se excluyen**: no traen desviación ni semáforo. → [formatos-parsing.md](formatos-parsing.md)
- **La cavidad se deduce de la ruta completa**, no del nombre: en `intern.05` las carpetas `c15/`
  y `c16/` tienen ficheros con el mismo nombre.
- **Las cabeceras repetidas se numeran** (`N170 BOLT 1 … H=5.0 mm` sale dos veces): sin eso el
  cruce entre muestreos se multiplica y falla.
- **El error de signo de B2/B4 se marca, no se corrige** por defecto (`--corregir-signo` lo hace).
- **Las fechas no salen en la interfaz**: los muestreos ya se ordenan por número, y lo relevante
  de cada uno es qué pasó antes (el retoque de molde). Las fechas viven en
  [3212/historial-molde.md](3212/historial-molde.md).
- **Una página por resultado, no scroll infinito**: además de navegarse mejor, evita el límite de
  ~16 contextos WebGL del navegador, que dejaba gráficos en blanco.
- **El PNG de cada PDF lleva muestreo + cavidad + elemento en el nombre**: los 144 PDF se llaman
  todos `PA_1`…`PB_6`, así que un nombre derivado solo de la carpeta hace que los de un muestreo
  **sobrescriban** a los de otro y cada página acabe mostrando la gráfica de otra tanda. Pasó, y
  el síntoma es silencioso: los enlaces siguen funcionando. La comprobación que lo caza es
  **contar imágenes distintas**, no solo que existan.

---

## Lo que confirmaron sobre los datos

🆕 **Cada CSV es UNA pieza, no un promedio.** `3212c14.csv` son las medidas de la única pieza que
salió del hueco 14 en esa tanda. Evidencia:

1. Las **12 gráficas de contorno** de una cavidad están tomadas en una **sesión continua de 4
   minutos** (10:50 → 10:54): no da tiempo a desmontar y realinear piezas distintas.
2. El `.igs` de esa misma carpeta lleva el timestamp `240119.105452` — el cierre de esa sesión.
3. El `DR(3D)` del XLS tiene **una sola columna por cavidad**.
4. `HISTORY` de `intern.09` anota *"Update to 5 pcs"*, señal de que hasta entonces era una.

📌 Los **MIN/MAX** que aparecen por todo el CSV **no son dos piezas**: son el valor mínimo y
máximo del mismo elemento en la misma pieza (el diámetro más estrecho y el más ancho del mismo
agujero, que es como se detecta la ovalidad).
