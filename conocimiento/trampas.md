# Trampas de los datos y recetas de lectura

Guía rápida para decidir cómo leer un dato. El detalle y sus cifras viven en la
[referencia temática](README.md#referencias-por-tema), no se duplican aquí.

### Receta: leer un `.xls` PPAP

Consultar primero `consultar.py celdas <id> --hoja "DR(3D)" --filas 12-20` y revisar
fórmulas y procedencia. Para extraer de nuevo, usar los [lectores de la biblioteca](README.md#cómo-se-actualiza):
reconocen PDF disfrazados de XLS y trabajan sobre copias cuando necesitan Excel.
No abrir el original con COM para recalcular o guardar.

### Receta: leer un CSV de CMM

Identificar primero el formato: CMM por bloques, comparativa, puntos o `#P#` no son la
misma tabla. Las columnas, codificación y claves del piloto están en
[Formatos y parsing](formatos-parsing.md#1-csv-de-medición-de-cavidad--el-formato-más-importante);
las variantes entre piezas, en [Comparativa](comparativa.md).

### Receta: sacar el texto de un PPTX de corrección

Buscar texto y localizadores con `consultar.py buscar` y `consultar.py ver` antes de abrir
el PPTX. Si la cota solo está en un recorte, localizar sus imágenes con la
[receta del PPTX](0-bolt-eye/3212/5-retoques-molde.md#receta-para-recuperar-el-n-number-de-una-diapositiva).
No confundir el orden físico de diapositivas con el número de acción impreso.

## Trampas que ya nos han mordido

1. **Un informe PPAP puede heredar resultados.** Para evaluaciones CMM coincidentes,
   contrastar los CSV de la tanda. [Discrepancias y fuentes](formatos-parsing.md#discrepancias-entre-medidas-xls-y-csv).
2. **XLS parcial no implica CMM parcial.** Comprobar la cobertura de cada export;
   [metrología del 3212](0-bolt-eye/3212/4-metrologia.md).
3. **El export del 3212 tiene errores de signo de posición.** Conservar originales y
   aplicar solo la corrección comprobada, no una regla universal.
   [Signos e identificación CMM](formatos-parsing.md#-trampas-del-csv).
4. **Un título puede identificar mal un elemento.** Usar la clave interna CMM y la
   evaluación, no solo el literal. [Claves](formatos-parsing.md#-el-id-de-elemento-cmm-es-el-join-key-interno).
5. **Los nombres cambian y pueden colisionar.** Conservar la ruta completa; la cavidad
   puede estar únicamente en la carpeta. [Casos de parsing](formatos-parsing.md#5-tabla-de-gotchas-consolidada).
6. **Hay varios idiomas en un mismo documento.** No limitar la búsqueda a español;
   las acciones pueden estar en catalán, inglés o alemán.
7. **El número de cavidad no es el número de cavidades del molde.** Para el piloto,
   [identidad y evidencia de cavidades](0-bolt-eye/3212/4-metrologia.md#la-cabecera--contrastar-las-hojas-del-mismo-libro).
8. **Localizar un globo no equivale a leerlo bien.** El escaneo del piloto requiere
   revisión de propuestas OCR. [Plano y pruebas](0-bolt-eye/3212/1-pieza-2d-3d.md).
9. **Fecha de PDF y revisión de plano son cosas distintas.** No asignar la revisión del
   PDF disponible a todos los informes. [Contraste del 3212](0-bolt-eye/3212/1-pieza-2d-3d.md#-este-plano-no-es-el-de-los-informes).
10. **La numeración de carpetas es una convención.** Una carpeta ausente puede tener su
    contenido en otra posición. [Estructuras encontradas](comparativa.md#lo-que-cambia-entre-piezas-lo-que-un-lector-genérico-tiene-que-admitir).
11. **El nombre `DR*` no garantiza función ni columnas.** Distinguir medición, previsión,
    croquis y comparación por su contenido. [Esquemas](formatos-parsing.md#2-xls-ppap--informe-dimensional-interno).
12. **Combinar cabeceras e HISTORY con su procedencia.** Una hoja vacía no demuestra que
    falte el dato en el libro. [Cabeceras y excepciones](0-bolt-eye/3212/4-metrologia.md#la-cabecera--contrastar-las-hojas-del-mismo-libro).
13. **IGES/TXT y DXF/TXT tienen relaciones distintas.** No deduplicar geometría por
    nombre o por comparar solo el primer punto.
    [Contraste completo](0-bolt-eye/3212/4-metrologia.md#rectificación-dxf-equivalente-con-redondeo-iges-con-z-aplanada).
14. **Fecha de informe no equivale a fecha de medición.** Guardar cada fecha con su fuente;
    no extender la fecha de un perfil a todas las mediciones de la tanda.
    [Fuentes geométricas](0-bolt-eye/3212/4-metrologia.md#rectificación-dxf-equivalente-con-redondeo-iges-con-z-aplanada).
15. **Un número guardado puede ser aleatorio, derivado o una previsión.** Consultar fórmula,
    dependencias y procedencia; la ausencia en `celda_aleatoria` no certifica una medida.
    [I-003 y recuentos vigentes](incongruencias.md#i-003-en-detalle).
16. **No elegir versiones por nombre o fecha de archivo.** Comparar contenido y registrar
    la variante usada. [PPTX del 3212](0-bolt-eye/3212/5-retoques-molde.md#qué-fichero-usar)
    e [incongruencias](incongruencias.md) (I-603).
17. **La extensión puede mentir.** La biblioteca reconoce la firma de un PDF con extensión
    XLS. Eso no significa que el importador de la app lo haga.
    [Lectores de conocimiento](README.md#cómo-se-actualiza) y [alcance de la app](../docs/cotas-y-evidencia-web.md#datos-y-alcance).
