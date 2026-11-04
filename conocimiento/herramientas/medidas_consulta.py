"""Consulta de derivadas CMM/perfil sin escritura ni dependencias del backend."""
import re


def consultar(con, pieza=None, documento=None, cota=None, hoja=None, cavidad=None, maximo=200):
    medidas, total, documentos, por_fuente = [], 0, 0, {}
    for tabla in ("medida_cmm", "medida_contorno"):
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (tabla,)).fetchone():
            continue
        if hoja and hoja != ("CSV" if tabla == "medida_cmm" else "PDF"):
            continue
        # PA/PB describe contour IDs. No N-number is invented for these profiles.
        if cota and tabla == "medida_contorno":
            continue
        where, args = ["d.estado='extraido'"], []
        if pieza:
            where.append("m.pieza=?")
            args.append(pieza)
        if documento is not None:
            where.append("m.documento_id=?")
            args.append(documento)
        if cota:
            where.append("m.cota=?")
            args.append(re.sub(r"(?i)^N", "", cota.strip()))
        if cavidad:
            where.append("m.cavidad=?")
            args.append("c" + re.sub(r"(?i)^(?:cav\.?\s*|c)", "", cavidad))
        sql = f"FROM {tabla} m JOIN documento d ON d.id=m.documento_id WHERE {' AND '.join(where)}"
        n, docs = con.execute("SELECT count(*),count(DISTINCT m.documento_id) " + sql, args).fetchone()
        total += n
        documentos += docs
        por_fuente[tabla] = n
        cur = con.execute("SELECT m.*,d.ruta " + sql + " ORDER BY m.muestreo,m.cavidad,d.ruta LIMIT ?", [*args, max(0, maximo - len(medidas))])
        names = [c[0] for c in cur.description]
        for values in cur:
            row = dict(zip(names, values))
            row.update(ruta="Exemples/" + row["ruta"], origen=tabla, hoja="CSV" if tabla == "medida_cmm" else "PDF")
            if tabla == "medida_cmm":
                row.update(cota_lector=row["cota"], cavidad_lector=row["cavidad"], valor_lector=row["valor"],
                           localizador=f"linea {row['fila']}", clasificacion="export_cmm",
                           celda_original={"valor": row["valor_original"], "formula": None, "formula_disponible": None})
            else:
                row.update(localizador="pagina 1, tabla Contorno/CONTORN", clasificacion="perfil_contorno",
                           aviso="ID de contorno; vinculo con una cota del plano no confirmado")
            medidas.append(row)
    return {"medidas": medidas, "total": total, "documentos": documentos, "por_fuente": por_fuente}
