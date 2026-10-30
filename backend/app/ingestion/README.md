# Lectores de la aplicación

Este paquete pertenece al backend. Recibe rutas explícitas del trabajador de evidencia
y devuelve datos estructurados e imágenes derivadas; no genera visores HTML ni abre
navegadores. No depende de `prototypes/`, rutas personales ni scripts externos al backend.

- `drawing.py`: texto PDF, detección de globos y su lectura. La caché y las revisiones humanas
  corresponden a `EvidenceJob` y `DrawingLocation`. Desde el 30/10/2026:
  - **Fuente globo a globo:** capa vectorial si el PDF trae los globos como vectores sobre el
    escaneo; si no, la imagen original.
  - **Detector en dos pasadas:** mide el tamaño típico de los globos del plano y busca solo los de
    ese tamaño.
  - **Orientación automática.**
- `balloon_reader.py`: lectura de los números con RapidOCR y el lector propio, votación de los
  dos y un número por plano. Solo se ofrece la lectura que llega al umbral de la fuente del globo.
  Si el modelo o sus metadatos faltan o no son válidos, los globos quedan localizados sin lectura
  automática y se muestra un aviso; la búsqueda en el texto del plano sigue disponible.
- `drawing_version.py`: identidad del lector (versión, huellas del ONNX y del JSON, y umbrales). Entra en la
  clave de caché del índice: cambiarla obliga a preparar de nuevo la búsqueda.
- `models/lector_globos.onnx`: el lector propio, una CRNN de 0,24 M parámetros entrenada solo con
  números sintéticos, sin datos del cliente. `lector_globos.json` lleva su alfabeto, la entrada y
  las huellas.
  - Se genera en el prototipo con
    `entrenar_lector_globos.py --perfil general --exportar-onnx …`, que comprueba que coincide
    con el modelo de torch.
  - El backend no usa torch.

El origen y las mediciones de todo esto están en el prototipo
(`prototypes/data-explorer/README.md`, desde «Comparativa de lectores de globos»). Lo portado
reproduce exactamente sus lecturas, comprobado en 5 planos reales el 30/10/2026. Las limitaciones
documentadas allí siguen vigentes:
- umbrales provisionales;
- lecturas ofrecidas sin verificar;
- negritas muy gruesas;
- solo globos verdes o azules;
- generalización sin demostrar.
- `cmm.py`: bloques CSV, identidad de filas y corrección documentada del signo B2/B4.
- `profile_pdf.py`: tablas y gráficas de los informes de perfiles.
- `common.py`: validez numérica y referencias al documento original.
- `pilot_3212/`: configuración de casos, catálogo, previsiones XLS, acciones PPTX y
  composición del snapshot. Sus correspondencias y convenciones son específicas del
  3212; no deben aplicarse a otras piezas sin configurar y validar otro adaptador.

`app.evidence_converter` ejecuta estos lectores en un subproceso. Las pruebas del backend
usan fuentes sintéticas; la construcción Docker excluye todos los prototipos.
