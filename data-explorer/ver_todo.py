"""
ver_todo.py - Punto de entrada unico. Genera los cuatro visores y la pantalla inicial.

Los visores viven en dos carpetas segun de donde salga el dato:

    metrologia/   lo que dejo la maquina de medicion (ver_csv, ver_txt, ver_pdf)
    planos/       el plano 2D del cliente (ver_plano)

Todos escriben en la MISMA carpeta `out/`, en la raiz de data-explorer, para que los
enlaces entre paginas sigan siendo relativos y la pantalla inicial sea una sola.

    out/index.html        <- SE ABRE ESTO
    ├── csv-3212.html     las cotas medidas y comparadas contra el plano
    ├── txt-3212.html     las nubes de puntos en bruto
    ├── pdf-3212.html     el perfil interior contra el contorno teorico
    └── plano-3212.html   el plano 2D con su texto localizable

Uso
---
    python data-explorer/ver_todo.py                 # genera los cuatro y abre el inicio
    python data-explorer/ver_todo.py --solo pdf      # regenera solo uno (y el inicio)
    python data-explorer/ver_todo.py --solo csv,txt
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import webbrowser
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "out"

VISORES = {
    "csv": {
        "script": "metrologia/ver_csv.py",
        "indice": "csv-3212.html",
        "carpeta": "csv",
        "titulo": "Las cotas medidas",
        "gancho": "Lo que la maquina midio y comparo contra el plano",
    },
    "txt": {
        "script": "metrologia/ver_txt.py",
        "indice": "txt-3212.html",
        "carpeta": "txt",
        "titulo": "Las nubes de puntos",
        "gancho": "Las coordenadas en bruto, antes de convertirse en cotas",
    },
    "pdf": {
        "script": "metrologia/ver_pdf.py",
        "indice": "pdf-3212.html",
        "carpeta": "pdf",
        "titulo": "La tolerancia de contorno",
        "gancho": "El perfil interior comparado contra el teorico",
    },
    "plano": {
        "script": "planos/ver_plano.py",
        "indice": "plano-3212.html",
        "carpeta": "plano",
        "titulo": "El plano 2D",
        "gancho": "El plano del cliente, con su texto buscable y marcable",
    },
}

ESTILO = """
:root { --linea: #e3e6ea; --tinta: #1a1a1a; --suave: #667; --azul: #3d6fb4; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "Segoe UI", sans-serif; margin: 0 auto; max-width: 1020px;
       padding: 64px 24px 80px; color: var(--tinta); background: #fff; line-height: 1.55; }
h1 { font-size: 32px; margin: 0 0 34px; letter-spacing: -0.025em; }
h2 { font-size: 18px; margin: 0 0 16px; font-weight: 600; }

.opciones { display: grid; grid-template-columns: repeat(auto-fit, minmax(215px, 1fr)); gap: 18px; }
@media (max-width: 620px) { .opciones { grid-template-columns: 1fr; } }
a.opcion { display: flex; flex-direction: column; text-decoration: none; color: var(--tinta);
           border: 1px solid var(--linea); border-radius: 12px; padding: 24px 22px 26px;
           transition: border-color .12s, box-shadow .12s, transform .12s; background: #fff; }
a.opcion:hover { border-color: var(--azul); box-shadow: 0 6px 20px rgba(61,111,180,.13);
                 transform: translateY(-2px); }
a.opcion .tipo { font-family: ui-monospace, Consolas, monospace; font-size: 12px;
                 letter-spacing: .1em; color: var(--azul); text-transform: uppercase; }
a.opcion h3 { font-size: 20px; margin: 8px 0 4px; letter-spacing: -0.02em; }
a.opcion .gancho { font-size: 14px; color: var(--suave); }
a.opcion .aviso { margin-top: 12px; font-size: 12.5px; color: var(--suave);
                  font-family: ui-monospace, Consolas, monospace; }
a.opcion.falta { opacity: .5; pointer-events: none; }
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--solo", help="regenerar solo estos visores, separados por coma: csv,txt,pdf")
    parser.add_argument("--solo-inicio", action="store_true",
                        help="rehacer solo index.html, sin volver a procesar los datos")
    parser.add_argument("--salida", type=Path, default=SALIDA)
    parser.add_argument("--no-abrir", action="store_true")
    args = parser.parse_args()

    if args.solo_inicio:
        cuales = []
    elif args.solo:
        cuales = [c.strip() for c in args.solo.split(",")]
    else:
        cuales = list(VISORES)
    desconocidos = [c for c in cuales if c not in VISORES]
    if desconocidos:
        sys.exit(f"Visor desconocido: {', '.join(desconocidos)}. Validos: {', '.join(VISORES)}")

    for clave in cuales:
        script = AQUI / VISORES[clave]["script"]
        print(f"\n=============== {script.name} ===============")
        resultado = subprocess.run(
            [sys.executable, str(script), "--no-abrir", "--salida", str(args.salida)],
            check=False,
        )
        if resultado.returncode != 0:
            sys.exit(f"{script.name} ha fallado (codigo {resultado.returncode})")

    tarjetas = []
    for clave, visor in VISORES.items():
        existe = (args.salida / visor["indice"]).exists()
        tarjetas.append(
            f"<a class='opcion{'' if existe else ' falta'}' href='{visor['indice']}'>"
            f"<span class='tipo'>{clave}</span>"
            f"<h3>{visor['titulo']}</h3>"
            f"<div class='gancho'>{visor['gancho']}</div>"
            + ("" if existe else
               "<div class='aviso'>sin generar &mdash; ejecuta ver_todo.py</div>")
            + "</a>"
        )

    cuerpo = (
        "<h1>3212 Pump Housing</h1>"
        "<h2>&iquest;Que quieres mirar?</h2>"
        f"<div class='opciones'>{''.join(tarjetas)}</div>"
    )
    fichero = args.salida / "index.html"
    fichero.write_text(
        f"<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>3212 Pump Housing - datos de medicion</title>"
        f"<style>{ESTILO}</style></head><body>{cuerpo}</body></html>",
        encoding="utf-8",
    )
    print(f"\n\nPantalla inicial: {fichero}")
    if not args.no_abrir:
        webbrowser.open(fichero.as_uri())


if __name__ == "__main__":
    main()
