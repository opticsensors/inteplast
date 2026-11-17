# Instrucciones para agentes

Leer `CLAUDE.md` para el contexto del repositorio. Antes de modificar la aplicación,
leer `docs/app-web.md`; para cambios de interfaz, también `docs/interfaz.md`.

## No completar fichas para compensar el algoritmo

**Instrucción expresa de Eduard, 16/11/2026.** La aplicación debe poder incorporar y
ampliar la base de datos sin un agente que interprete y rellene cada pieza.

- No elegir ni corregir manualmente datos de las fichas de trabajo: plano principal,
  asociaciones de componentes, hojas, revisiones, nombres, cliente u otros campos.
  No sustituir el resultado del algoritmo con conocimiento del agente sobre una pieza.
- Conservar el resultado del algoritmo aunque sea incorrecto y registrar el fallo como
  pendiente. Corregir la regla general y comprobarla con casos representativos.
- Si los datos no permiten automatizarlo, documentar qué información o convenciones
  debe aportar INTEPLAST, o proporcionar una selección explícita al usuario en la app.
  La decisión manual corresponde al usuario, no al agente.
- Una autorización para probar, desplegar o importar no autoriza a escoger por cuenta
  propia valores que el algoritmo no deduce. Aplicar elecciones concretas de una ficha
  solo cuando el usuario indique esas elecciones expresamente.
- Las configuraciones manuales de pruebas deben quedar identificadas y separadas de
  la validación del proceso automático. No presentar una ficha preparada manualmente
  como prueba de que la selección de carpeta funciona de forma general.
- No ocultar estos fallos con reglas exclusivas para un código de pieza. Las incidencias
  técnicas se conservan en el registro del servidor y en la documentación, fuera de la GUI.

El 3288 fue configurado manualmente durante las pruebas del 16/11/2026. Esa intervención
no demuestra automatización. Estado y corrección de la estrella en
`docs/proximos-pasos.md`, apartado «Rectificación: ninguna selección manual del agente».
