"""Inventario de Exemples: una fila por fichero, solo con metadatos.

No abre ningun fichero (no hidrata placeholders de OneDrive). Un fichero cuyo tamano o
fecha cambian vuelve a quedar 'pendiente' de extraer; uno que desaparece queda 'eliminado'.

    conocimiento/.venv/Scripts/python.exe conocimiento/herramientas/inventariar.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import (  # noqa: E402
    EXEMPLES, NUBE, ahora, cerrar_registro, clasificar, conectar, larga, registrar, ruta_relativa,
)


def main() -> None:
    if not EXEMPLES.is_dir():
        sys.exit(f"No se encuentra Exemples: {EXEMPLES}")
    con = conectar()
    ejecucion = registrar(con, "inventariar", {"exemples": str(EXEMPLES)})
    previos = {
        ruta: (tamano, mtime, estado)
        for ruta, tamano, mtime, estado in con.execute(
            "SELECT ruta, tamano, mtime_ns, estado FROM documento"
        )
    }
    vistos: set[str] = set()
    nuevos = cambiados = 0
    marca = ahora()
    raiz_larga = larga(EXEMPLES)
    for directorio, carpetas, ficheros in os.walk(raiz_larga):
        carpetas.sort()
        for nombre in sorted(ficheros):
            completo = os.path.join(directorio, nombre)
            info = os.stat(completo, follow_symlinks=False)  # metadatos: no descarga el contenido
            ruta = ruta_relativa(EXEMPLES / os.path.relpath(completo, raiz_larga))
            vistos.add(ruta)
            atributos = getattr(info, "st_file_attributes", 0)
            datos = {
                **clasificar(ruta),
                "ruta": ruta,
                "nombre": nombre,
                "ext": Path(nombre).suffix.lower().lstrip("."),
                "tamano": info.st_size,
                "mtime_ns": info.st_mtime_ns,
                "atributos": atributos,
                "en_nube": int(bool(atributos & NUBE)),
                "inventariado_el": marca,
            }
            previo = previos.get(ruta)
            if previo is None:
                nuevos += 1
                columnas = ", ".join(datos)
                con.execute(
                    f"INSERT INTO documento({columnas}) VALUES ({', '.join('?' * len(datos))})",
                    list(datos.values()),
                )
                continue
            cambio = (previo[0], previo[1]) != (info.st_size, info.st_mtime_ns)
            if cambio or previo[2] == "eliminado":
                cambiados += 1
                datos["estado"] = "pendiente"
                datos["sha256"] = None
            asignaciones = ", ".join(f"{k}=?" for k in datos)
            con.execute(
                f"UPDATE documento SET {asignaciones} WHERE ruta=?", [*datos.values(), ruta]
            )
    eliminados = [r for r in previos if r not in vistos and previos[r][2] != "eliminado"]
    con.executemany(
        "UPDATE documento SET estado='eliminado' WHERE ruta=?", [(r,) for r in eliminados]
    )
    con.commit()
    total = len(vistos)
    resumen = {"total": total, "nuevos": nuevos, "cambiados": cambiados,
               "eliminados": len(eliminados)}
    cerrar_registro(con, ejecucion, resumen)
    print(resumen)
    for feature, n, mb, nube in con.execute(
        "SELECT feature, count(*), round(sum(tamano)/1e6,1), sum(en_nube) FROM documento "
        "WHERE estado!='eliminado' GROUP BY feature ORDER BY feature"
    ):
        print(f"  {feature:<28} {n:>5} ficheros {mb:>9} MB  nube={nube}")
    con.close()


if __name__ == "__main__":
    main()
