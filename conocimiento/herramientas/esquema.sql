-- Biblioteca de los datos de Exemples. Se regenera desde los originales; no es fuente de verdad.
-- Las conclusiones revisadas viven en los Markdown y en hallazgos.jsonl (en Git).

-- Un fichero de Exemples. `ruta` es relativa a Exemples, con '/'.
CREATE TABLE IF NOT EXISTS documento (
  id               INTEGER PRIMARY KEY,
  ruta             TEXT NOT NULL UNIQUE,
  feature          TEXT,              -- '0- Bolt Eye', '1- Clips en Piezas'...
  grupo            TEXT,              -- nivel intermedio opcional ('Tipo A' en Clips)
  pieza            TEXT,              -- carpeta de la pieza ('3212 Pump Housing', '3205')
  codigo           TEXT,              -- prefijo numerico de la pieza ('3212')
  carpeta          TEXT,              -- primera carpeta dentro de la pieza, tal cual
  carpeta_norm     TEXT,              -- pieza_2d3d|moldflow|molde|metrologia|retoques|metodo_medida|stl_real|otro|raiz
  nombre           TEXT NOT NULL,
  ext              TEXT NOT NULL,     -- en minusculas, sin punto ('' si no tiene)
  tamano           INTEGER NOT NULL,
  mtime_ns         INTEGER NOT NULL,
  atributos        INTEGER,           -- atributos de Windows al inventariar
  en_nube          INTEGER NOT NULL DEFAULT 0,  -- placeholder de OneDrive al inventariar
  sha256           TEXT,              -- se calcula al extraer
  estado           TEXT NOT NULL DEFAULT 'pendiente',
    -- pendiente | extraido | solo_metadatos | sin_texto | duplicado | error | eliminado
  lector           TEXT,
  mensaje          TEXT,              -- error o aviso del lector
  duplicado_de     INTEGER REFERENCES documento(id),
  inventariado_el  TEXT NOT NULL,
  extraido_el      TEXT,
  version_extraida TEXT               -- tamano:mtime_ns:lector@version de la ultima extraccion
);
CREATE INDEX IF NOT EXISTS documento_feature ON documento(feature, pieza, carpeta_norm);
CREATE INDEX IF NOT EXISTS documento_ext ON documento(ext);
CREATE INDEX IF NOT EXISTS documento_sha ON documento(sha256);

-- Unidades de contenido con localizador: diapositiva, pagina, parrafo, fila de hoja, bloque CSV...
CREATE TABLE IF NOT EXISTS elemento (
  id           INTEGER PRIMARY KEY,
  documento_id INTEGER NOT NULL REFERENCES documento(id) ON DELETE CASCADE,
  tipo         TEXT NOT NULL,
  localizador  TEXT NOT NULL,       -- 'diapositiva 33', 'DR(3D)!14', 'pagina 1', 'linea 120'
  orden        INTEGER NOT NULL,
  texto        TEXT,
  datos        TEXT                 -- JSON opcional (imagenes de la diapositiva, recuentos...)
);
CREATE INDEX IF NOT EXISTS elemento_doc ON elemento(documento_id, orden);

-- Celdas de hojas de calculo y CSV, con su coordenada original.
CREATE TABLE IF NOT EXISTS celda (
  documento_id INTEGER NOT NULL REFERENCES documento(id) ON DELETE CASCADE,
  hoja         TEXT NOT NULL,       -- nombre de hoja; 'csv' para CSV
  fila         INTEGER NOT NULL,    -- 1-based, como en Excel
  col          INTEGER NOT NULL,    -- 1-based
  valor        TEXT,                -- valor mostrado/guardado como texto
  numero       REAL,                -- valor numerico si lo es
  formula      TEXT,                -- solo XLSX/XLSM (XLS BIFF8 no conserva el texto de la formula)
  PRIMARY KEY (documento_id, hoja, fila, col)
) WITHOUT ROWID;

-- Huella de estructura por fichero: hojas, cabeceras, patrones. Sirve para comparar features.
CREATE TABLE IF NOT EXISTS estructura (
  documento_id INTEGER NOT NULL REFERENCES documento(id) ON DELETE CASCADE,
  clave        TEXT NOT NULL,
  valor        TEXT,
  PRIMARY KEY (documento_id, clave)
) WITHOUT ROWID;

-- Busqueda de texto completo sobre los elementos (sin acentos, multilingue).
CREATE VIRTUAL TABLE IF NOT EXISTS elemento_fts USING fts5(
  texto, content='elemento', content_rowid='id', tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS elemento_ai AFTER INSERT ON elemento BEGIN
  INSERT INTO elemento_fts(rowid, texto) VALUES (new.id, new.texto);
END;
CREATE TRIGGER IF NOT EXISTS elemento_ad AFTER DELETE ON elemento BEGIN
  INSERT INTO elemento_fts(elemento_fts, rowid, texto) VALUES ('delete', old.id, old.texto);
END;
CREATE TRIGGER IF NOT EXISTS elemento_au AFTER UPDATE ON elemento BEGIN
  INSERT INTO elemento_fts(elemento_fts, rowid, texto) VALUES ('delete', old.id, old.texto);
  INSERT INTO elemento_fts(rowid, texto) VALUES (new.id, new.texto);
END;

-- Registro de ejecuciones, para saber que se proceso y con que resultado.
CREATE TABLE IF NOT EXISTS ejecucion (
  id          INTEGER PRIMARY KEY,
  herramienta TEXT NOT NULL,
  parametros  TEXT,
  inicio      TEXT NOT NULL,
  fin         TEXT,
  resumen     TEXT
);
