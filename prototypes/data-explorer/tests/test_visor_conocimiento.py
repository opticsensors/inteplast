"""Visor de conocimiento: datos, grafo y revisión sobre la biblioteca real (se omiten sin ella)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "conocimiento"))
import datos  # noqa: E402

pytestmark = pytest.mark.skipif(not datos.BD.is_file(), reason="sin biblioteca.sqlite")


def test_planos_unicos_con_pieza():
    planos = datos.planos()
    assert planos
    assert len({p["id"] for p in planos}) == len(planos)
    assert all(p["codigo"] for p in planos)


def test_globos_calibrados_caen_en_la_pagina():
    calibrado = next(p for p in datos.planos() if p["calibradas"])
    g = datos.globos(calibrado["id"], calibrado["calibradas"][0])
    assert g["metodo"] == "calibrada" and g["globos"]
    dentro = sum(-0.02 <= b["x"] <= 1.02 and -0.02 <= b["y"] <= 1.02 for b in g["globos"])
    assert dentro / len(g["globos"]) > 0.95


def test_planos_de_lado_quedan_horizontales_con_sus_globos():
    from PIL import Image

    girados = [p for p in datos.planos() if p["nombre"] in datos.GIROS]
    assert {p["nombre"] for p in girados} == set(datos.GIROS)
    assert all(p["giro"] == datos.GIROS[p["nombre"]] for p in girados)  # cambia la dirección de la imagen
    assert datos.girar_punto(1, 0, 90) == (1, 1)  # el cajetín arriba a la derecha baja a su sitio
    assert datos.girar_punto(0, 1, 270) == (1, 1)  # el cajetín abajo a la izquierda pasa a la derecha
    for p in girados:
        ruta = datos.imagen(p["id"], 1, "mini")
        if ruta:  # sin el original en local no se puede dibujar
            with Image.open(ruta) as im:
                assert im.width > im.height
        for b in datos.globos(p["id"], 1)["globos"]:
            assert -0.02 <= b["x"] <= 1.02 and -0.02 <= b["y"] <= 1.02


def test_con_icp_es_un_solo_tag_y_los_globos_traen_punta():
    con_icp = [p for p in datos.planos() if p["icp"]]
    assert con_icp and all(p["tag"] == "icp" for p in con_icp)
    assert all(p["tag"] in datos.TAGS or p["tag"] is None for p in datos.planos())
    g = datos.globos(con_icp[0]["id"], 1)
    assert g["globos"] and all(b["etiqueta"] and {"px", "py"} <= set(b) for b in g["globos"])


def test_plano_a_otra_escala_usa_la_calibracion_de_su_gemela():
    p = next((x for x in datos.planos() if x["nombre"] == "20231129_885253-11250_insulator_motor_v1.pdf"), None)
    assert p
    g = datos.globos(p["id"], 1)
    assert g["metodo"] == "gemela" and len(g["globos"]) >= 200
    assert sum(0 <= b["x"] <= 1 and 0 <= b["y"] <= 1 for b in g["globos"]) / len(g["globos"]) > .95


@pytest.mark.parametrize("texto, cota", [("N170", "170"), ("No. 200", "200"), ("[]247", "247"), ("□133", "133"), ("1080.3", "1080.3")])
def test_la_cota_se_busca_con_su_marca(texto, cota):
    assert datos.normaliza_cota(texto) == cota


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
    import leer_planos

    assert [(e, n) for e, n, *_ in leer_planos.marcas_en_token(texto)] == esperado


def test_numero_cortado_por_la_tesela_no_cuenta_dos_veces():
    import leer_planos

    base = {"p": 1, "s": .9, "via": "[]", "w": .01, "h": .01}
    marcas = [{**base, "t": "27", "x": .500, "y": .5}, {**base, "t": "271", "x": .503, "y": .5}, {**base, "t": "27", "x": .9, "y": .9}]
    assert sorted(m["t"] for m in leer_planos.sin_repetir(marcas)) == ["27", "271"]


def test_la_cuarta_cifra_pegada_a_una_marca_de_tres_no_cuenta():
    import leer_planos

    base = {"p": 1, "s": .9, "via": "[]", "w": .01, "h": .01, "y": .5}
    tres = [{**base, "t": str(100 + i), "x": .1 * i} for i in range(9)]
    pegada = {**base, "t": "1980", "x": .95}
    assert "198" in [m["t"] for m in leer_planos.recorta_cuadros(tres + [pegada])]
    # Con mayoría de cuatro cifras, la cuarta sí es parte del número.
    cuatro = [{**base, "t": str(1000 + i), "x": .1 * i} for i in range(9)]
    assert "1980" in [m["t"] for m in leer_planos.recorta_cuadros(cuatro + [pegada])]


def test_el_texto_no_se_lee_boca_abajo():
    import leer_planos

    assert leer_planos.sentido_admitido(0) and leer_planos.sentido_admitido(269.1) and leer_planos.sentido_admitido(45)
    assert not leer_planos.sentido_admitido(180) and not leer_planos.sentido_admitido(135)


@pytest.mark.parametrize("args, tag", [
    ((863, 629, 0, 0, 0., 0.), "globos"),
    ((125, 2, 0, 0, 0., 0.), "nada"),  # aros sin números: cotas resaltadas, no globos
    ((1, 0, 180, 0, 0., 0.), "numerado"),
    ((0, 0, 0, 0, 0., .99), "numerado"),
    ((0, 0, 0, 45, 1., 0.), "numerado"),
    ((0, 0, 0, 30, .1, 0.), "nada"),  # recuadros que no son las cotas de los informes
    ((0, 0, 0, 0, 0., .1), "nada"),
])
def test_decide_un_solo_tag(args, tag):
    import leer_planos

    assert leer_planos.decide_tag(*args) == tag


def test_los_numeros_de_cada_pieza_son_los_de_su_ficha():
    for fila in datos.piezas():
        if fila["codigo"] not in ("3212", "3288", "3309"):
            continue
        ficha = datos.pieza(fila["codigo"])
        assert fila["muestreos"] == len(ficha["muestreos"])
        assert fila["cotas"] == len(ficha["cotas"])
        assert fila["correcciones"] == len(ficha["cadenas"])
        assert fila["hallazgos"] == len(ficha["hallazgos"])
        assert fila["casos"] == len(ficha["casos"])


def test_cada_pieza_tiene_su_cad():
    cad = {p["codigo"]: p["cad"] for p in datos.piezas()}
    assert all(cad.values())
    assert len(cad["3288"]) == 2  # base y tapa


def test_tolerancias_redondeadas_agrupan_ruido_de_coma_flotante():
    assert datos.tolerancia({"nominal": 0.8, "tol_sup": 0.0499999999999999, "tol_inf": -0.05}) == (0.8, 0.05, -0.05)


def test_grafo_sin_aristas_colgantes():
    import grafo

    g = grafo.construir()
    ids = {n["id"] for n in g["nodos"]}
    assert all(a["source"] in ids and a["target"] in ids for a in g["aristas"])
    assert {"pieza", "hallazgo", "pregunta", "feature"} <= {n["tipo"] for n in g["nodos"]}


def test_grafo_de_piezas_une_por_feature_y_por_ficheros_con_sentido():
    import grafo

    g = grafo.piezas_y_features()
    ids = {n["id"] for n in g["nodos"]}
    assert all(a["source"] in ids and a["target"] in ids for a in g["aristas"])
    assert {n["tipo"] for n in g["nodos"]} == {"pieza", "feature", "familia"}
    familias = {a["target"]: [] for a in g["aristas"] if a["tipo"] == "familia"}
    for a in g["aristas"]:
        if a["tipo"] == "familia":
            familias[a["target"]].append(a["source"])
    assert sorted(familias["familia:Pump Housing"]) == ["pieza:2820", "pieza:3051", "pieza:3212"]
    assert next(n for n in g["nodos"] if n["id"] == "familia:Isomask")["supuesta"] is True
    con_feature = {a["source"] for a in g["aristas"] if a["tipo"] == "feature"}
    assert con_feature == {n["id"] for n in g["nodos"] if n["tipo"] == "pieza"}
    identicos = {(a["source"], a["target"]): a["ficheros"] for a in g["aristas"] if a["tipo"] == "identicos"}
    assert len(identicos[("pieza:3205", "pieza:3206")]) == 6  # el utillaje de medida: pdf, stp y CATPart
    # Coinciden sin decir nada de las piezas: caché del navegador, PDF vacío y README de remisión.
    assert ("pieza:3174", "pieza:3309") not in identicos
    assert ("pieza:3174", "pieza:3205") not in identicos
    assert ("pieza:3195", "pieza:3226") not in identicos


def test_tags_de_las_piezas():
    tags = {p["codigo"]: p["tag"] for p in datos.piezas()}
    assert [c for c, t in tags.items() if t == "nada"] == ["2820"]
    assert sorted(c for c, t in tags.items() if t == "medidas") == ["3226", "3233"]
    assert tags["3056"] == "correcciones"  # plan en imágenes: la cuenta automática lo daría sin correcciones
    assert sum(t == "correcciones" for t in tags.values()) == 18
    assert all(p["tag_motivo"] for p in datos.piezas() if p["codigo"] in datos.TAG_FIJO)


def test_familias_sin_piezas_repetidas():
    piezas = [c for f in datos.FAMILIAS.values() for c in f["piezas"]]
    assert len(piezas) == len(set(piezas))
    assert all(f["fuente"] for f in datos.FAMILIAS.values())
    assert [n for n, f in datos.FAMILIAS.items() if f.get("supuesta")] == ["Isomask"]
    assert {p["codigo"]: p["familia"] for p in datos.piezas()}["3197"] is None


def medida(n=1, hoja="DR", fila=10, col=8, cav="c1", valor=1.0, doc=None, ruta=None, nombre=None, bloque=1, serie="00",
           equipo="cmm", etiqueta="", comentario="", marca=None, tol=(1.0, .5, -.5)):
    nombre = nombre or f"9999-{serie}_intern.{n:02d}.xls"
    return {"doc": doc or n, "nombre": nombre, "ruta": ruta or f"x/Interns/{nombre}", "hoja": hoja, "fila": fila, "col": col, "cota": "5", "cav": cav,
            "valor": valor, "serie": serie, "n": n, "elemento": (etiqueta, "", tol, equipo, comentario), "marca": marca, "bloque": bloque}


def lineas(s, cav="c1"):
    return s["puntos"][cav]


def test_falta_la_pestana_se_rellena_con_punto_hueco():
    import evolucion

    s = evolucion.construir([medida(n=1, hoja="DR_CMM", valor=1.1), medida(n=2, hoja="DR_CMM", valor=1.2), medida(n=3, hoja="DR", valor=1.3)], pestana="DR_CMM")
    a, b, c = lineas(s)
    assert (a["hueco"], b["hueco"], c["hueco"]) == (False, False, True)
    assert c["v"] == 1.3 and "DR_CMM" in c["avisos"][0] and "«DR»" in c["avisos"][0]
    assert s["resumen"]["huecos"] == 1


def test_sin_ese_elemento_no_hay_punto_ni_muestreo():
    import evolucion

    s = evolucion.construir([medida(n=1, valor=1.1, etiqueta="a"), medida(n=2, valor=1.2, etiqueta="b")], elemento=None)
    assert len(s["muestreos"]) == 1 and len(s["sin_elemento"]) == 1


def test_filas_sin_rotulo_son_elementos_distintos():
    import evolucion

    s = evolucion.construir([medida(fila=10, valor=1.1), medida(fila=11, valor=1.2)])
    assert [e["etiqueta"] for e in s["elementos"]] == ["CMM · fila 1", "CMM · fila 2"]
    assert lineas(s)[0]["v"] == 1.1
    assert lineas(evolucion.construir([medida(fila=10, valor=1.1), medida(fila=11, valor=1.2)], elemento=s["elementos"][1]["id"]))[0]["v"] == 1.2


def test_la_misma_fila_en_dos_bloques_usa_el_ultimo_y_avisa():
    import evolucion

    p = lineas(evolucion.construir([medida(fila=10, valor=1.1, bloque=1), medida(fila=50, col=8, valor=1.4, bloque=3)]))[0]
    assert p["v"] == 1.4 and p["celda"] == "H50"
    assert any("1,1" in a and "fila 10" in a for a in p["avisos"])


def test_varias_piezas_de_una_cavidad_dan_la_media_rotulada():
    import evolucion

    p = lineas(evolucion.construir([medida(col=8, valor=1.0), medida(col=16, valor=2.0)]))[0]
    assert p["v"] == 1.5 and p["media"] == 2


def test_columnas_identicas_no_son_una_media():
    import evolucion

    p = lineas(evolucion.construir([medida(col=8, valor=1.0), medida(col=16, valor=1.0)]))[0]
    assert p["v"] == 1.0 and p["media"] is None


def test_las_muestras_de_una_cavidad_son_una_sola_linea():
    import evolucion

    s = evolucion.construir([medida(col=10, cav="c1.m1", valor=1.0), medida(col=11, cav="c1.m2", valor=2.0)])
    assert s["cavidades"] == ["c1"] and lineas(s)[0]["media"] == 2


def test_copias_que_discrepan_usa_interns_y_avisa():
    import evolucion

    filas = [medida(doc=1, ruta="x/Customer/a.xls", valor=1.9), medida(doc=2, ruta="x/Interns/a.xls", valor=1.1)]
    p = lineas(evolucion.construir(filas))[0]
    assert p["v"] == 1.1 and p["carpeta"] == "Interns"
    assert any("Customer" in a and "1,9" in a for a in p["avisos"])


def test_copias_iguales_no_avisan():
    import evolucion

    filas = [medida(doc=1, ruta="x/Customer/a.xls", valor=1.1), medida(doc=2, ruta="x/Interns/a.xls", valor=1.1)]
    assert lineas(evolucion.construir(filas))[0]["avisos"] == []


def test_muestreo_repetido_se_dibuja_y_se_marca():
    import evolucion

    s = evolucion.construir([medida(n=1, valor=1.1), medida(n=2, valor=1.3), medida(n=3, valor=1.1)])
    a, b, c = lineas(s)
    assert c["v"] == 1.1 and c["repite"] == "intern.01" and a["repite"] is None and b["repite"] is None
    assert any("No sabemos" in x for x in c["avisos"])


def test_excluidos_no_se_dibujan_y_se_listan():
    import evolucion

    s = evolucion.construir([medida(n=1, valor=1.1), medida(n=2, valor=7.0, marca="aleatoria")])
    assert len(s["muestreos"]) == 1
    assert [(x["valor"], x["muestreo"]) for x in s["excluidos"]] == [(7.0, "intern.02")]


def csv_de_prueba(n, *valores, cav="c1", nominal=1.0):
    return {("00", n, cav, nominal): [{"nombre": "a.csv", "carpeta": "support", "fila": 100 + i, "valor": v, "lim": [.5, 1.5]} for i, v in enumerate(valores)]}


def test_el_csv_manda_sobre_el_excel_y_lo_avisa():
    import evolucion

    p = lineas(evolucion.construir([medida(valor=1.1)], csv_de_prueba(1, 1.25)))[0]
    assert p["v"] == 1.25 and p["csv"]["linea"] == 100
    assert any("1,25" in a and "1,1" in a for a in p["avisos"])


def test_el_csv_se_cruza_por_posicion_y_confirma_si_coincide():
    import evolucion

    filas = [medida(fila=10, valor=1.1), medida(fila=11, valor=1.2)]
    s = evolucion.construir(filas, csv_de_prueba(1, 1.1, 1.2005))
    assert lineas(s)[0]["v"] == 1.1 and lineas(s)[0]["csv"]["linea"] == 100 and lineas(s)[0]["avisos"] == []
    segundo = evolucion.construir([dict(x) for x in filas], csv_de_prueba(1, 1.1, 1.2005), elemento=s["elementos"][1]["id"])
    assert lineas(segundo)[0]["v"] == 1.2 and lineas(segundo)[0]["csv"]["linea"] == 101


def test_el_csv_no_toca_filas_de_otro_equipo():
    import evolucion

    p = lineas(evolucion.construir([medida(valor=1.1, equipo="caliper")], csv_de_prueba(1, 1.25)))[0]
    assert p["v"] == 1.1 and p["csv"] is None


def test_fila_de_otro_equipo_junto_a_filas_de_cmm_no_rompe():
    import evolucion

    filas = [medida(fila=10, valor=1.1, equipo="cmm"), medida(fila=11, valor=1.2, equipo="caliper")]
    s = evolucion.construir(filas, csv_de_prueba(1, 1.1))
    calibre = next(e["id"] for e in s["elementos"] if "CALIPER" in e["etiqueta"])
    p = lineas(evolucion.construir([dict(x) for x in filas], csv_de_prueba(1, 1.1), elemento=calibre))[0]
    assert p["v"] == 1.2 and p["csv"] is None


def test_muestreo_solo_en_el_csv_tambien_se_dibuja():
    import evolucion

    s = evolucion.construir([medida(n=1, valor=1.1)], {**csv_de_prueba(1, 1.1), **csv_de_prueba(3, 1.3)})
    assert [m["n"] for m in s["muestreos"]] == [1, 3]
    assert lineas(s)[1]["v"] == 1.3 and lineas(s)[1]["hoja"] == evolucion.HOJA_CSV


def test_csv_con_otro_numero_de_filas_no_se_cruza_por_posicion():
    import evolucion

    p = lineas(evolucion.construir([medida(valor=1.1)], csv_de_prueba(1, 1.4, 1.5)))[0]
    assert p["v"] == 1.1 and p["csv"] is None and any("no se ha podido cruzar" in a for a in p["avisos"])


def test_los_tramos_no_cruzan_series_y_llevan_sus_correcciones():
    import evolucion

    s = evolucion.construir([medida(n=1, valor=1.1), medida(n=2, valor=1.2), medida(n=5, valor=1.3), medida(n=1, serie="10", valor=1.4, doc=9)])
    assert [(t["de"], t["a"]) for t in s["tramos"]] == [(0, 1), (1, 2)]
    corr = {"serie": "00", "origen": 2, "validacion": 5}
    otra = {"serie": "00", "origen": None, "validacion": 2}
    sin_nada = {"serie": "00", "origen": None, "validacion": None}
    evolucion.asociar_correcciones(s, [corr, otra, sin_nada])
    assert [t["correcciones"] for t in s["tramos"]] == [[1], [0]]
    assert s["correcciones_sin_tramo"] == 1


def test_la_tolerancia_que_cambia_no_dibuja_banda():
    import evolucion

    fija = evolucion.construir([medida(n=1, valor=1.1), medida(n=2, valor=1.2)])
    assert fija["banda"] == {"inf": .5, "sup": 1.5} and not fija["tolerancia_cambia"]
    cambia = evolucion.construir([medida(n=1, valor=1.1), medida(n=2, valor=1.2, tol=(1.0, .1, -.1))])
    assert cambia["banda"] is None and cambia["tolerancia_cambia"]


def test_parrafos_quitan_la_plantilla_de_la_diapositiva():
    import evolucion

    texto = "Tool correction nº1 – P3212\t\t24/01/2024\n1/37\nLongitud 70mm\nTool correction 1.1 (DIM. Nr.214) Ø16\nCurrent situation:\nFer creixer el plastic en Ø0,23mm"
    assert evolucion.parrafos(texto) == ["Fer creixer el plastic en Ø0,23mm"]
    assert evolucion.parrafos("9\nHacer algo") == ["Hacer algo"]  # el número de página suelto tampoco es texto


def test_3212_cota_113_con_datos_reales():
    import evolucion

    s = evolucion.serie("3212", "113")
    assert [e["etiqueta"] for e in s["elementos"]][:2] == ["1 · CMM", "2 · CMM"]
    por_muestreo = {m["n"]: p for m, p in zip(s["muestreos"], s["puntos"]["c13"])}
    assert por_muestreo[3]["v"] == 3.056
    assert por_muestreo[5]["v"] == 3.042 and any("3,056" in a for a in por_muestreo[5]["avisos"])  # el Excel repite .03
    assert por_muestreo[8]["v"] == 3.074 and por_muestreo[8]["celda"] == "H52"  # el bloque antiguo está en la fila 25
    assert por_muestreo[8]["hueco"] and any("3,297" in a and "fila 25" in a for a in por_muestreo[8]["avisos"])
    assert por_muestreo[2]["repite"] == "intern.01" and por_muestreo[9]["repite"] == "intern.01"
    assert s["banda"] == {"inf": 3.0, "sup": 3.1}
    assert any(t["correcciones"] for t in s["tramos"])
    assert s["correcciones"][0]["numero"] == "1.34" and "Retoc" in s["correcciones"][0]["variantes"][0]["texto"][0]


def paso(numero="1.1", documento=1, diapositiva=1, texto=("Hacer algo",), preferente=False, **extra):
    return {"numero": numero, "fecha": "2024-01-01", "serie": "00", "origen": 1, "validacion": 2, "estado": "valores nuevos", "pptx": f"plan{documento}.pptx",
            "carpeta": "retoques", "documento": documento, "diapositiva": diapositiva, "avisos": [], "texto": list(texto), "preferente": preferente,
            "componente": None, **extra}


def copias_de(acciones):
    return sorted((c["documento"], c["diapositiva"]) for a in acciones for v in a["variantes"] for c in v["copias"])


def test_las_copias_con_el_mismo_texto_comparten_variante_sin_perder_fichero():
    import evolucion

    [accion] = evolucion.agrupar_correcciones([paso(documento=1), paso(documento=2)])
    assert len(accion["variantes"]) == 1 and not accion["textos_distintos"]
    assert copias_de([accion]) == [(1, 1), (2, 1)]


def test_una_variante_con_otro_texto_no_desaparece():
    import evolucion

    [accion] = evolucion.agrupar_correcciones([paso(documento=1, texto=["Ø0,22"]), paso(documento=2, texto=["Ø0,21"])])
    assert [v["texto"] for v in accion["variantes"]] == [["Ø0,22"], ["Ø0,21"]] and accion["textos_distintos"]


def test_acciones_distintas_con_el_mismo_texto_no_se_juntan():
    import evolucion

    assert len(evolucion.agrupar_correcciones([paso(numero="1.1"), paso(numero="1.2", diapositiva=2)])) == 2  # otro número
    assert len(evolucion.agrupar_correcciones([paso(numero=None, documento=1), paso(numero=None, documento=2)])) == 2  # sin número no se sabe
    [misma] = evolucion.agrupar_correcciones([paso(documento=1, diapositiva=1), paso(documento=1, diapositiva=2)])  # dos diapositivas no son copias
    assert len(misma["variantes"]) == 2


def test_diapositivas_sin_texto_no_se_toman_por_iguales():
    import evolucion

    [accion] = evolucion.agrupar_correcciones([paso(documento=1, texto=[]), paso(documento=2, texto=[])])
    assert len(accion["variantes"]) == 2


def test_la_variante_preferente_va_primero_y_no_oculta_las_otras():
    import evolucion

    [accion] = evolucion.agrupar_correcciones([paso(documento=1, texto=["borrador"]), paso(documento=2, texto=["final"], preferente=True)])
    assert [(v["texto"], v["preferente"]) for v in accion["variantes"]] == [(["final"], True), (["borrador"], False)]


def test_3212_correccion_2_15_conserva_las_dos_cifras():
    import evolucion

    [accion] = [x for x in evolucion.serie("3212", "162")["correcciones"] if x["numero"] == "2.15"]
    textos = [" ".join(v["texto"]) for v in accion["variantes"]]
    assert len(textos) == 2 and "Ø0,22mm" in textos[0] and "Ø0,21mm" in textos[1]
    assert accion["variantes"][0]["preferente"] and not accion["variantes"][1]["preferente"]  # rev1, elegida en la ficha del 3212
    assert accion["variantes"][1]["copias"][0]["pptx"].endswith("_rev1_.pptx")


def test_3212_correccion_1_28_prefiere_lo_documentado_y_conserva_el_borrador():
    import evolucion

    [accion] = [x for x in evolucion.serie("3212", "243")["correcciones"] if x["numero"] == "1.28"]
    assert accion["variantes"][0]["copias"][0]["pptx"].endswith("_rev1.pptx") and "0,29mm" in accion["variantes"][0]["texto"][0]
    assert accion["variantes"][1]["copias"][0]["pptx"].endswith("_rev0.pptx") and "DRAFT" in accion["variantes"][1]["texto"]


def test_3051_diapositivas_distintas_de_un_mismo_fichero_siguen_separadas():
    import evolucion

    c = datos.con()
    copias = copias_de(evolucion.correcciones(c, "3051", "1100"))
    assert len(copias) == c.execute("SELECT count(*) FROM cadena_correccion WHERE pieza='3051' AND cota='1100'").fetchone()[0] > 1
    assert len(set(copias)) == len(copias)


def test_ninguna_correccion_de_la_biblioteca_desaparece():
    import evolucion

    c = datos.con()
    filas = [tuple(f) for f in c.execute("SELECT pieza, cota, documento_id, diapositiva FROM cadena_correccion")]
    por_cota = {}
    for pieza, cota, documento, diapositiva in filas:
        por_cota.setdefault((pieza, cota), []).append((documento, diapositiva))
    for (pieza, cota), esperado in por_cota.items():
        assert copias_de(evolucion.correcciones(c, pieza, cota)) == sorted(esperado), (pieza, cota)


def test_los_planos_del_3288_dicen_su_componente():
    componentes = {p["id"]: p["componente"] for p in datos.planos() if p["codigo"] == "3288"}
    assert componentes[3029] == "base" and componentes[3122] == "tapa" and componentes[3113] == "conjunto"
    assert all(componentes.values()) and sorted(set(componentes.values())) == ["base", "conjunto", "tapa"]
    assert not any(p["componente"] for p in datos.planos() if p["codigo"] != "3288")


@pytest.mark.parametrize("componente, nominal, valor, hoja", [("base", .2, .19, "DR(base)"), ("tapa", 2.2, 2.13, "DR(tapa)")])
def test_3288_cabecera_y_grafica_son_del_mismo_componente(componente, nominal, valor, hoja):
    import app

    r = app.cota("3288", "77", componente=componente)
    assert r["componente"] == componente and r["hoja"] == hoja
    por_muestreo = {m["n"]: p for m, p in zip(r["muestreos"], r["puntos"]["c10"])}
    assert por_muestreo[3]["v"] == valor and por_muestreo[3]["hoja"] == hoja
    assert all(p["hoja"].casefold().find(componente) >= 0 for lista in r["puntos"].values() for p in lista if p)
    assert [n[0] for n in r["info"]["nominal"]] == [nominal]  # la cabecera no mezcla la nominal de la otra pieza
    assert r["banda"] == {"inf": round(nominal - .1, 6), "sup": round(nominal + .1, 6)}


def test_3288_los_recuentos_de_cada_componente_suman_el_total():
    base, tapa = datos.resumen_cota("3288", "77", "base"), datos.resumen_cota("3288", "77", "tapa")
    todo = datos.resumen_cota("3288", "77")
    assert base["medidas"] + tapa["medidas"] == todo["medidas"] and base["medidas"] and tapa["medidas"]
    assert base["excluidas"] + tapa["excluidas"] == todo["excluidas"]


def test_3288_las_correcciones_son_las_de_su_componente():
    import evolucion

    tapa = evolucion.serie("3288", "77", componente="tapa")["correcciones"]
    assert {x["numero"] for x in tapa} == {"1.1", "2.1"} and all(x["componente"] == "tapa" for x in tapa)
    assert evolucion.serie("3288", "77", componente="base")["correcciones"] == []
    assert datos.resumen_cota("3288", "77", "base")["correcciones"] == 0 and datos.resumen_cota("3288", "77", "tapa")["correcciones"] == 2


def test_3288_pestana_elegida_decide_el_componente_y_no_se_rellena_con_la_otra():
    import evolucion

    s = evolucion.serie("3288", "77", "DR(tapa)")
    assert s["componente"] == "tapa" and {h["hoja"] for h in s["hojas"]} <= {"DR(tapa)", "DR(tapa)param", "TAPA"}
    assert not any(p["hueco"] and "base" in p["hoja"].casefold() for lista in s["puntos"].values() for p in lista if p)
    assert [x["id"] for x in s["componentes"]] == ["base", "tapa"]


def test_3288_una_cota_de_una_sola_pieza_abre_en_esa_pieza():
    import evolucion

    ficha = datos.pieza("3288")
    for nombre in ("base", "tapa"):
        cota = next(x["cota"] for x in ficha["cotas"] if set(x["por_componente"]) == {nombre})
        assert evolucion.serie("3288", cota)["componente"] == nombre


def valores_por_componente(c, documento, cota):
    """Valores no excluidos de una cota (o sus subpuntos, si no tiene) en las hojas de informe de un documento."""
    cuenta = {"base": 0, "tapa": 0}
    filas = c.execute("SELECT m.cota, m.hoja, m.marca FROM medida_dr m JOIN lectura_dr l ON l.documento_id = m.documento_id AND l.hoja = m.hoja"
                      " WHERE m.documento_id = ? AND (m.cota = ? OR m.cota LIKE ?) AND l.papel = 'informe' AND m.valor IS NOT NULL",
                      (documento, cota, cota + ".%")).fetchall()
    exactas = [f for f in filas if f["cota"] == cota]
    for f in exactas or filas:
        if f["marca"] not in datos.EXCLUIDAS:
            cuenta[datos.componente_de_nombre("3288", f["hoja"])] += 1
    return cuenta


def test_3288_cadena_cota_58_solo_cuenta_la_base():
    f = datos.con().execute("SELECT * FROM cadena_correccion WHERE pieza = '3288' AND cota = '58'").fetchone()
    assert (f["numero"], f["origen_n"], f["origen_fuera"]) == ("1.2", 20, 0)  # antes, 30/60: los 30 eran de la tapa
    assert (f["validacion_n"], f["validacion_fuera"]) == (16, 0)  # antes, 30/56
    assert "nominales distintos" not in f["avisos"]


def test_3288_ningun_paso_de_la_cadena_mezcla_componentes():
    c = datos.con()
    filas = c.execute("SELECT ca.*, d.nombre AS pptx FROM cadena_correccion ca JOIN documento d ON d.id = ca.documento_id WHERE ca.pieza = '3288'").fetchall()
    assert len(filas) == 32
    for f in filas:
        componente = datos.componente_de_nombre("3288", f["pptx"])
        assert componente, f["pptx"]
        for documento, n in ((f["origen_documento_id"], f["origen_n"]), (f["validacion_documento_id"], f["validacion_n"])):
            if documento is not None:
                assert n == valores_por_componente(c, documento, f["cota"])[componente], (f["cota"], f["numero"], documento)


def test_3288_la_repeticion_de_la_base_ya_no_marca_parcial_a_la_tapa():
    estados = [f[0] for f in datos.con().execute("SELECT validacion_estado FROM cadena_correccion WHERE pieza = '3288'")]
    assert estados.count("nueva") == 25 and estados.count(None) == 7


def test_3288_plan_3_de_la_tapa_no_parte_de_valores_de_la_base():
    c = datos.con()
    filas = c.execute("SELECT numero, cota, fuente_origen, origen_muestreo, origen_n, origen_fuera, validacion_muestreo, avisos FROM cadena_correccion"
                      " WHERE pieza = '3288' AND numero IN ('3.1', '3.2', '3.3', '3.4')").fetchall()
    assert len(filas) == 4
    for f in filas:
        # El XLS de su carpeta es intern.03, pero su DR(tapa) no trae estas cotas: los 20 valores de antes eran de la base.
        assert (f["fuente_origen"], f["origen_muestreo"], f["origen_n"], f["validacion_muestreo"]) == ("fecha", 2, 16, 4)
        assert "el XLS de la carpeta indica intern.03" in f["avisos"]


def test_ficha_del_3288_recuentos_por_componente():
    ficha = datos.pieza("3288")
    assert ficha["componentes"] == datos.COMPONENTES["3288"]
    cota = next(x for x in ficha["cotas"] if x["cota"] == "77")
    assert set(cota["por_componente"]) == {"base", "tapa"}
    assert cota["por_componente"]["base"]["medidas"] + cota["por_componente"]["tapa"]["medidas"] == cota["medidas"]
    assert {x["componente"] for x in ficha["cadenas"]} == {"base", "tapa"}


def test_una_pieza_normal_no_tiene_componentes():
    import evolucion

    s = evolucion.serie("3212", "113")
    assert s["componente"] is None and s["componentes"] == []
    assert evolucion.serie("3212", "113", componente="base")["componente"] is None  # no se inventa uno


def test_si_todo_esta_excluido_siguen_los_valores_y_sus_motivos():
    import evolucion

    s = evolucion.construir([medida(n=1, valor=0.0, marca="cero"), medida(n=2, valor=7.0, marca="aleatoria")])
    assert s["elemento"] is None and s["muestreos"] == []
    assert [(x["valor"], x["motivo"]) for x in s["excluidos"]] == [(0.0, datos.EXCLUIDAS["cero"]), (7.0, datos.EXCLUIDAS["aleatoria"])]


def test_3168_cota_1610_muestra_sus_20_valores_excluidos():
    import evolucion

    s = evolucion.serie("3168", "1610")
    assert s["elemento"] is None and len(s["excluidos"]) == 20
    assert {x["motivo"] for x in s["excluidos"]} == {datos.EXCLUIDAS["cero"]}
    assert all(x["fichero"] and x["celda"] and x["muestreo"] for x in s["excluidos"])


@pytest.mark.parametrize("palabra, cota, si", [
    ("30", "30", True), ("30.1", "30", True), ("30.3", "30", True), ("N30", "30", True), ("No.30", "30", True), ("[]30", "30", True), ("30,", "30", True),
    ("130", "30", False), ("230", "30", False), ("20230906", "30", False), ("3", "30", False), ("300", "30", False), ("30.1", "30.1", True), ("30.12", "30.1", False),
])
def test_es_la_cota(palabra, cota, si):
    assert datos.es_la_cota(palabra, cota) is si


def test_plano_3237_con_marca_encuentra_la_cota_y_sus_subcotas():
    plano = next(p for p in datos.planos() if p["nombre"] == "20260914_3130589019 2D 05.pdf")
    if not datos.estado_onedrive(plano["ruta"])[0]:
        pytest.skip("el original no está en local")
    texto = [x["texto"] for x in datos.buscar_en_plano(plano["id"], "30")["resultados"]]
    assert "130" in texto and "20230906" in texto  # sin marca sigue siendo búsqueda de texto
    for consulta in ("N30", "n30", "No. 30", "[]30"):
        assert sorted(x["texto"] for x in datos.buscar_en_plano(plano["id"], consulta)["resultados"]) == ["30", "30", "30", "30.1", "30.3"]


def test_revision_guarda_todos_los_casos_y_la_presentacion_los_recorta():
    import revision

    r = revision.revisar()
    m13 = next(x for x in r["comprobaciones"] if x["id"] == "M13")
    assert m13["n"] == 565 == len(m13["casos"])
    md = revision.markdown(r)
    assert "Se muestran 25 de 565" in md and "revision.json" in md


def test_piezas_de_otras_plantillas_dibujan_alguna_cota():
    import evolucion

    for codigo in ("3214", "3309"):
        assert any(evolucion.serie(codigo, c["cota"])["muestreos"] for c in datos.pieza(codigo)["cotas"][:5])


def test_revision_cuenta_y_ejemplos_coherentes():
    import revision

    r = revision.revisar()
    for x in r["comprobaciones"]:
        assert len(x["casos"]) == x["n"]
        assert x["nivel"] in {"ok", "info", "aviso"}
        assert (x["n"] == 0) == (x["nivel"] == "ok") or x["nivel"] == "info"
