# Lectores de la aplicación

Este paquete pertenece al backend. Recibe rutas explícitas del trabajador de evidencia
y devuelve datos estructurados e imágenes derivadas; no genera visores HTML ni abre
navegadores. No depende de `prototypes/`, rutas personales ni scripts externos al backend.

- `drawing.py`: texto PDF, globos y propuestas OCR. La caché y las revisiones humanas
  corresponden a `EvidenceJob` y `DrawingLocation`; se conservan las coordenadas y los
  identificadores de candidatos para no invalidar revisiones de los mismos bytes.
- `cmm.py`: bloques CSV, identidad de filas y corrección documentada del signo B2/B4.
- `profile_pdf.py`: tablas y gráficas de los informes de perfiles.
- `common.py`: validez numérica y referencias al documento original.
- `pilot_3212/`: configuración de casos, catálogo, previsiones XLS, acciones PPTX y
  composición del snapshot. Sus correspondencias y convenciones son específicas del
  3212; no deben aplicarse a otras piezas sin configurar y validar otro adaptador.

`app.evidence_converter` ejecuta estos lectores en un subproceso. Las pruebas del backend
usan fuentes sintéticas; la construcción Docker excluye todos los prototipos.
