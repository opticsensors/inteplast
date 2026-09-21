# Prototipos

Herramientas de exploración para entender los datos y probar ideas. Se conservan
en este repositorio, pero no forman parte de la aplicación web ni de su imagen Docker.

- [Data Explorer](data-explorer/README.md): visores experimentales de planos,
  metrología y correcciones. Sus salidas generadas permanecen fuera de Git.
- Los lectores de la web viven en `backend/app/ingestion/`, con pruebas propias.
  El backend y el frontend no deben importar, ejecutar ni copiar código de esta carpeta.

Un prototipo puede servir como referencia para implementar una función de producto.
La lógica que llegue a la web debe incorporarse y mantenerse en el backend, sin
depender de que el prototipo siga existiendo. Los scripts de exploración conservan
sus dependencias locales y sus rutas configurables a datos externos.
