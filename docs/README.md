# Documentación de la aplicación

Entrada para desarrollar sin contexto previo. **Revisado contra el código el 26/10/2026**;
la revisión documental no sustituye una prueba de ejecución. Los resultados de pruebas
anteriores conservan su fecha. Los datos y su evidencia pertenecen a
[conocimiento/](../conocimiento/README.md), que tiene herramientas y una SQLite propias:
su cobertura no implica que el importador de la aplicación soporte los mismos formatos.

## Dónde consultar y actualizar cada tema

| Necesidad | Documento de referencia | Estado que describe |
|---|---|---|
| Entender la aplicación, sus entidades, permisos y arranque | [Aplicación web](app-web.md) | Implementado en el código |
| Importar y consultar cotas, mediciones y correcciones | [Cotas y evidencia](cotas-y-evidencia-web.md) | Contrato actual y límites del piloto |
| Buscar, navegar y consultar gráficos o planos | [Interfaz](interfaz.md) | Comportamiento actual de la UI |
| Acceder a originales, SharePoint y visores PDF/3D | [Ficheros externos](ficheros-externos.md) | Implementado; prueba real de SharePoint pendiente |
| Convertir CAD grandes a GLB y gestionar su cola | [Vistas 3D](vistas-3d.md) | Implementado y límites conocidos |
| Elegir caras, encuadres y capturas del CAD | [Portadas CAD](portadas-cad.md) | Implementado y limitaciones de actualización |
| Chat, herramientas, fuentes y concurrencia | [Asistente](asistente.md) | Implementado; decisiones de despliegue pendientes |
| Generalizar la lectura a otras familias | [Ingesta automática](ingesta-automatica.md) | Análisis y propuesta; separa prototipos de producción |
| Diseñar el modelo normalizado del dominio | [Modelo de datos](modelo-datos.md) | Propuesta, con correspondencia explícita a tablas reales |
| Consultar el alcance futuro | [Hoja de ruta](hoja-de-ruta.md) | Etapas y condiciones para avanzar |
| Elegir la siguiente tarea | [Próximos pasos](proximos-pasos.md) | Pendientes resumidos, enlazados al detalle |
| Preparar preguntas al cliente | [Preguntas abiertas](preguntas-abiertas.md) | Dudas vigentes y resoluciones enlazadas a evidencia |

Leer primero la visión general y después solo el documento del tema. Consultar su código
enlazado antes de cambiar el contrato. Si cambia un comportamiento, actualizar su referencia
y el estado del backlog; los resúmenes deben enlazarla, no reproducir sus tablas o parámetros.

## Historial

- [Revisión del 15/09/2026](revision-2026-09-15.md): resultados de aquella revisión.
- [Acta del 24/09/2026](acta-reunion-2026-09-24.md): acuerdos y peticiones de la reunión.
- [Revisión documental del 26/10/2026](revision-2026-10-26.md): alcance, fuentes y límites
  de la revisión completa de `docs/` y la consolidación documental.

Un acuerdo del acta o una idea del modelo no equivale a una función implementada. Para una
cifra o interpretación de los originales, seguir la [referencia temática de conocimiento](../conocimiento/README.md#referencias-por-tema).
