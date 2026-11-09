"""Lectores de planos comunes (lectores_planos.py): marcas, recuadros, uso de .icp y dependencias.

Sin ficheros del cliente. La detección y la lectura de globos se prueban en
test_probar_lector_planos.py, test_comparar_ocr_globos.py y test_buscar_en_plano.py.
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

EXPLORER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPLORER))
import lectores_planos as lectores  # noqa: E402


# ---------------------------------------------------------------- marcas `[]` y `No.`

@pytest.mark.parametrize("texto, esperado", [
    ("[]246", [("[]", "246")]),
    ("1.8 ±0.15 []247", [("[]", "247")]),
    ("[]25 1", [("[]", "251")]),
    ("No.508", [("No.", "508")]),
    ("No.407 Φ3.55 ±0.05", [("No.", "407")]),
    ("ADDED NOTE No.15.", []),
    ("No.100 - No.108", []),
    ("VIEW No. 1", []),
    ("DIM NO.504 WAS 3X5.65 ±0.07", []),
    ("[]", []),
])
def test_marcas_propias_del_plano(texto, esperado):
    assert [(e, n) for e, n, *_ in lectores.marcas_en_token(texto)] == esperado


def test_numero_cortado_por_la_tesela_no_cuenta_dos_veces():
    base = {"p": 1, "s": .9, "via": "[]", "w": .01, "h": .01}
    marcas = [{**base, "t": "27", "x": .500, "y": .5}, {**base, "t": "271", "x": .503, "y": .5}, {**base, "t": "27", "x": .9, "y": .9}]
    assert sorted(m["t"] for m in lectores.sin_repetir(marcas)) == ["27", "271"]


def test_la_cuarta_cifra_pegada_a_una_marca_de_tres_no_cuenta():
    base = {"p": 1, "s": .9, "via": "[]", "w": .01, "h": .01, "y": .5}
    tres = [{**base, "t": str(100 + i), "x": .1 * i} for i in range(9)]
    pegada = {**base, "t": "1980", "x": .95}
    assert "198" in [m["t"] for m in lectores.recorta_cuadros(tres + [pegada])]
    # Con mayoría de cuatro cifras, la cuarta sí es parte del número.
    cuatro = [{**base, "t": str(1000 + i), "x": .1 * i} for i in range(9)]
    assert "1980" in [m["t"] for m in lectores.recorta_cuadros(cuatro + [pegada])]


# ---------------------------------------------------------------- recuadros

def test_el_texto_no_se_lee_boca_abajo():
    assert lectores.sentido_admitido(0) and lectores.sentido_admitido(269.1) and lectores.sentido_admitido(45)
    assert not lectores.sentido_admitido(180) and not lectores.sentido_admitido(135)


# ---------------------------------------------------------------- .icp

def sello(etiqueta, x1, y1, x2, y2):
    return {"etiqueta": etiqueta, "x1": x1, "y1": y1, "x2": x2, "y2": y2}


def test_la_calibracion_situa_cabeza_y_punta_segun_el_punto_elegido():
    # x' = 0,001·x + 0,5 ; y' = -0,002·(signo·y) + 0,5, con signo -1: y' = 0,002·y + 0,5.
    cal = {"matriz": [[.001, 0, .5], [0, -.002, .5]], "punto": 1, "signo": -1}
    (g,) = lectores.sellos_calibrados([sello("12", 10., 20., 100., 50.)], cal)
    # punto 1: la cabeza es (x2, y2) y la punta (x1, y1).
    assert g["etiqueta"] == "12"
    assert (g["x"], g["y"]) == pytest.approx((.6, .6))
    assert (g["px"], g["py"]) == pytest.approx((.51, .54))


def test_el_calco_1a1_falla_si_los_sellos_se_salen_de_la_hoja():
    a4 = (841.89, 595.28)  # A4 apaisado en puntos: 297 × 210 mm
    dentro = [sello(str(i), -100. + 10 * i, 50., 0., 0.) for i in range(20)]
    assert len(lectores.sellos_a_escala(dentro, *a4)) == 20
    assert lectores.sellos_a_escala(dentro, *a4)[0]["x"] == pytest.approx(.5 - 100 / 297)
    fuera = sello("99", 400., 0., 0., 0.)  # x = 0,5 + 400/297: fuera de la hoja
    assert len(lectores.sellos_a_escala(dentro + [fuera], *a4)) == 20  # 20 de 21 dentro: más del 95 %
    assert lectores.sellos_a_escala(dentro[:10] + [fuera], *a4) is None  # 10 de 11: menos del 95 %
    assert lectores.sellos_a_escala([], *a4) == []


def test_la_gemela_es_otro_plano_con_el_mismo_icp_y_la_misma_forma():
    calibraciones = {"10-p1": {"icp": "a.icp"}, "11-p1": {"icp": "b.icp"}, "12-p1": {"icp": "a.icp", "id": "buena"}}
    formas = {(10, "1"): 1.414, (11, "1"): 1.414, (12, "1"): 1.4142}
    gemela = lectores.calibracion_gemela(calibraciones, "a.icp", 10, 1.4142, lambda d, n: formas.get((d, n)))
    assert gemela == {"icp": "a.icp", "id": "buena"}  # el propio 10 no cuenta; el 11 es de otro .icp
    assert lectores.calibracion_gemela(calibraciones, "a.icp", 10, 1.0, lambda d, n: formas.get((d, n))) is None


# ---------------------------------------------------------------- dependencias

def modulos_importados(ruta: Path) -> set[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    nombres = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres |= {a.name for a in nodo.names}
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            nombres.add(nodo.module)
    return nombres


def test_el_visor_y_los_scripts_de_medida_no_usan_la_aplicacion_final():
    """Un solo código de lectura de planos en el prototipo: nadie vuelve a importar backend/app."""
    ficheros = [EXPLORER / n for n in ("lectores_planos.py", "buscar_en_plano.py", "probar_lector_planos.py",
                                       "comparar_ocr_globos.py", "entrenar_lector_globos.py", "muestra_verificacion.py")]
    ficheros += [EXPLORER / "conocimiento" / n for n in ("leer_planos.py", "datos.py")]
    for ruta in ficheros:
        assert not {m for m in modulos_importados(ruta) if m == "app" or m.startswith("app.")}, ruta.name
        assert '"backend"' not in ruta.read_text(encoding="utf-8"), ruta.name  # p. ej. sys.path con REPO / "backend"


def test_el_modulo_comun_no_necesita_torch():
    codigo = (f"import sys; sys.path.insert(0, {str(EXPLORER)!r}); import lectores_planos; "
              "print('torch' in sys.modules)")
    salida = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, check=True)
    assert salida.stdout.strip() == "False"
