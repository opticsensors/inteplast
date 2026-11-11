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
        # Los errores, con lo que enseña la pestaña Errores (la ficha ya no los cuenta).
        import errores

        assert fila["errores"] == sum(i["pendiente"] for i in errores.de_pieza(fila["codigo"])["incidencias"])
        assert fila["generales"] == sum(i["pendiente"] for i in errores.generales(fila["codigo"])["incidencias"])


def test_el_desglose_de_ficheros_suma_la_columna_de_numeros():
    for fila in datos.piezas():
        d = datos.ficheros(fila["codigo"])
    from collections import Counter

    especiales = Counter()
    for fila in datos.piezas():
        d = datos.ficheros(fila["codigo"])
        assert d["total"]["n"] == fila["documentos"] == sum(x["n"] for x in d["carpetas"])
        assert "db" not in {t["ext"] for t in d["total"]["tipos"]}  # sin Thumbs.db: no son ficheros del proyecto
        exts = [t["ext"] for t in d["total"]["tipos"]]
        if "pdf" in exts and datos.ESCANEADO in exts:
            assert exts.index(datos.ESCANEADO) == exts.index("pdf") + 1  # juntos
        finales = [e for e in exts if e in (datos.VACIOS, datos.OTROS_SIN_TEXTO)]
        assert exts[len(exts) - len(finales):] == finales  # al final
        for x in d["carpetas"] + [d["total"]]:
            assert sum(t["n"] for t in x["tipos"]) == x["n"]  # cada fichero, en un solo tipo: no se cuenta dos veces
        for t in d["total"]["tipos"]:
            especiales[t["ext"]] += t["n"]
    # Los 4 PDF de 0 bytes y cav_1..4.txt del 3237 (solo saltos de línea); 3 Excel/ODS y 2 Word hechos de imágenes.
    assert (especiales[datos.VACIOS], especiales[datos.OTROS_SIN_TEXTO]) == (8, 5)
    # Las copias cuentan como su original: 3205-C.pdf y 3205-D.pdf del 3206 son escaneos del 3205.
    n3206 = {t["ext"]: t["n"] for t in datos.ficheros("3206")["total"]["tipos"]}
    assert n3206[datos.ESCANEADO] == 18
    c = datos.con()
    for codigo in ("3205", "3206", "3212"):
        pdf = c.execute(f"SELECT count(*), sum(estado_real='sin_texto') FROM {datos.CON_ORIGINAL} WHERE codigo=? AND lower(ext)='pdf'"
                        " AND tamano > 0", (codigo,)).fetchone()
        n = {t["ext"]: t["n"] for t in datos.ficheros(codigo)["total"]["tipos"]}
        assert (n.get("pdf", 0) + n.get(datos.ESCANEADO, 0), n.get(datos.ESCANEADO, 0)) == (pdf[0], pdf[1] or 0)


def test_cada_pieza_tiene_su_cad():
    cad = {p["codigo"]: p["cad"] for p in datos.piezas()}
    assert all(cad.values())
    assert len(cad["3288"]) == 2  # base y tapa


def test_tolerancias_redondeadas_agrupan_ruido_de_coma_flotante():
    assert datos.tolerancia({"nominal": 0.8, "tol_sup": 0.0499999999999999, "tol_inf": -0.05}) == (0.8, 0.05, -0.05)


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


def test_la_ficha_de_cota_del_plano_distingue_pieza_sin_medidas_de_cota_sin_medidas():
    """En el plano: «la pieza no tiene medidas leídas» (2820) no es «sin medidas de esta cota» (3212, 99999)."""
    sin_informes = datos.resumen_cota("2820", "260")
    assert not sin_informes["pieza_con_medidas"] and sin_informes["en_informes"]["medidas"] == 0
    otra_cota = datos.resumen_cota("3212", "99999")
    assert otra_cota["pieza_con_medidas"] and otra_cota["en_informes"]["medidas"] == 0
    con_medidas = datos.resumen_cota("3212", "113")
    # En el plano cuentan todas las medidas de los informes, también las de ficheros sin intern.NN.
    assert con_medidas["en_informes"]["medidas"] == con_medidas["medidas"] + con_medidas["sin_muestreo"] > 0


def test_las_medidas_csv_de_la_ficha_son_las_de_la_grafica():
    import evolucion

    assert evolucion.resumen_csv("2820", "260") is None  # sin CSV leídos de la pieza: «no leídos», no «sin medidas»
    csv = evolucion.resumen_csv("3212", "113")
    puntos = [p for lista in evolucion.csv_de(datos.con(), "3212", "113").values() for p in lista]
    assert csv == {"medidas": len(puntos), "ficheros": len({p["nombre"] for p in puntos})} and csv["medidas"] > 0
    assert evolucion.resumen_csv("3212", "99999") == {"medidas": 0, "ficheros": 0}


def test_marcar_cotas_con_datos_coincide_con_la_ficha():
    """Una cota sale en verde si y solo si su ficha tiene medidas (Excel o CSV) o alguna corrección."""
    import evolucion

    assert evolucion.cotas_con_datos("2820") == {"cotas": [], "pieza_con_datos": False}
    marcadas = set(evolucion.cotas_con_datos("3212")["cotas"])
    etiquetas = sorted({b["etiqueta"] for b in datos.globos(329, 1)["globos"]}, key=datos.clave_cota)
    for cota in etiquetas[::8] + ["99999"]:  # una de cada ocho del plano, y una que no existe
        ficha = datos.resumen_cota("3212", cota)["en_informes"]["medidas"] or evolucion.resumen_csv("3212", cota)["medidas"] \
            or len(evolucion._datos_cota("3212", cota)[2])
        assert (cota in marcadas) == bool(ficha), cota


def test_tag_de_datos_de_cada_plano():
    """«Cotas con datos» si alguno de sus números situados tiene datos; si no, «sin», también con 0 de 0."""
    import evolucion

    tags = evolucion.datos_de_planos()
    assert set(tags) == {p["id"] for p in datos.planos()}
    assert all((t["datos"] == "con") == (t["numeros_con_datos"] > 0) for t in tags.values())
    assert tags[1] == {"datos": "sin", "numeros_con_datos": 0, "numeros": 166}  # 2820: pieza sin nada leído
    assert tags[2507] == {"datos": "sin", "numeros_con_datos": 0, "numeros": 0}  # 3237: numeración en la capa de texto
    assert tags[329]["datos"] == "con"  # 3212 rev. 07


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


def test_csv_de_sin_condiciones_y_comparativa_solo_sin_individual():
    import sqlite3

    import evolucion

    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript("""
        CREATE TABLE documento (id INTEGER, nombre TEXT, ruta TEXT);
        CREATE TABLE medida_cmm (documento_id INTEGER, pieza TEXT, muestreo TEXT, cavidad TEXT, variante TEXT, fila INTEGER,
                                 bloque TEXT, cota TEXT, nominal REAL, tol_sup REAL, tol_inf REAL, valor REAL);
        CREATE TABLE medida_cmm_comparativa (documento_id INTEGER, pieza TEXT, muestreo TEXT, cavidad TEXT, variante TEXT,
                                             fila INTEGER, rotulo TEXT, bloque TEXT, cota TEXT, nominal REAL, tol_sup REAL, tol_inf REAL,
                                             valor REAL);
        INSERT INTO documento VALUES (1, 'c1-3197.csv', 'x/Support_intern.03/c1-3197.csv'),
                                     (2, '3197 C1.csv', 'x/Support_intern.02/140ºC/600bar/3197 C1.csv'),
                                     (3, 'totes-3197.csv', 'x/Support_intern.03/totes-3197.csv'),
                                     (4, '3197-totes.csv', 'x/Support_intern.09/3197-totes.csv'),
                                     (5, '3197_totes_nozzle 55.csv', 'x/Support_intern.08/3197_totes_nozzle 55.csv');
        INSERT INTO medida_cmm VALUES (1, '3197', '03', 'c1', NULL, 10, 'N230 ø4 (GX) Hole 1', '230', 4, .1, 0, 4.07),
                                      (2, '3197', '02', 'c1@140ºC/600bar', '140ºC/600bar', 10, 'N230 ø4 (GX) Hole 1', '230', 4, .1, 0, 4.05);
        INSERT INTO medida_cmm_comparativa VALUES (3, '3197', '03', 'c1', NULL, 20, 'c1', 'N230 ø4 (GX) Hole 1', '230', 4, .1, 0, 4.07),
                                                  (4, '3197', '09', 'c1', NULL, 7, 'c1', 'N230 ø4 (GX) Hole 1', '230', 4, NULL, NULL, 4.08),
                                                  (5, '3197', '08', 'c1@nozzle 55', 'nozzle 55', 7, 'c1', 'N230 ø4 (GX) Hole 1', '230', 4, NULL, NULL, 4.09);
    """)
    csv = evolucion.csv_de(c, "3197", "230")
    assert set(csv) == {("00", 3, "c1", 4.0), ("00", 9, "c1", 4.0)}  # sin condición; totes solo en .09
    assert [r["nombre"] for r in csv[("00", 3, "c1", 4.0)]] == ["c1-3197.csv"]
    assert csv[("00", 9, "c1", 4.0)][0]["columna"] == "c1" and csv[("00", 9, "c1", 4.0)][0]["lim"] is None
    assert csv[("00", 9, "c1", 4.0)][0]["bloque"] == "N230 ø4 (GX) Hole 1"
    p = evolucion.solo_csv(csv[("00", 9, "c1", 4.0)], 0)
    assert p["celda"] == "línea 7, columna c1" and p["csv"]["columna"] == "c1"


def medida_cmm(tipo, comentario, nominal, **kw):
    """Fila de CMM con el rótulo en el tipo (`max`, `gg`), como en los DR del 3197."""
    x = medida(**kw)
    x["elemento"] = ("", tipo, (nominal, .05, -.1), "cmm (dg0216)", comentario)
    return x


def csv_bloques(n, nominal, *filas, cav="c1"):
    return {("00", n, cav, nominal): [{"nombre": "c1.csv", "carpeta": f"Support_intern.{n:02d}", "fila": linea, "bloque": bloque,
                                       "valor": v, "lim": None} for linea, bloque, v in filas]}


def test_el_csv_no_cambia_un_maximo_por_un_minimo():
    # 3197 intern.07: DR!I59 es la cota 310 MAX (1,485); el CSV numera N310 el mínimo (1,429, línea 132) y N310.1 el máximo.
    import evolucion

    filas = [medida_cmm("max", "36 points", 1.5, n=7, fila=59, valor=1.485)]
    p = lineas(evolucion.construir(filas, csv_bloques(7, 1.5, (132, "N310 Thickness 1,5 (Min-Value / 36 Points)  - No ICL dimension", 1.429))))[0]
    assert p["v"] == 1.485 and p["csv"] is None
    assert any("no se ha podido cruzar" in a for a in p["avisos"])


def test_el_csv_no_cambia_una_altura_por_otra_ni_rellena_con_ella():
    # 3197 intern.05: la cota 550 a -4,5 mm (DR!I85) y a -8,5 mm (DR!I89, otro bloque); el CSV solo trae X=-4,5 (línea 92).
    import evolucion

    def filas():  # intern.07 solo trae la de -4,5 (DR!I113): ahí la posición es inequívoca y permite rellenar intern.03
        return [medida_cmm("gg", "h=-4.5 mm", 61.4, n=5, fila=85, valor=61.27, bloque=1),
                medida_cmm("gg", "h=-8.5 mm a la punta", 61.4, n=5, fila=89, valor=61.385, bloque=2),
                medida_cmm("gg", "h=-4.5 mm", 61.4, n=7, fila=113, valor=61.293, bloque=1)]

    csv = {**csv_bloques(5, 61.4, (92, "N550 ø61,4 (GG) X=-4,5", 61.27)), **csv_bloques(3, 61.4, (92, "N550 ø61,4 (GG) X=-4,5", 60.723))}
    s = evolucion.construir(filas(), csv)
    punta = next(e["id"] for e in s["elementos"] if "8.5" in e["etiqueta"])
    abajo = next(e["id"] for e in s["elementos"] if "4.5" in e["etiqueta"])
    a = evolucion.construir(filas(), csv, elemento=punta)
    assert [m["n"] for m in a["muestreos"]] == [5]  # intern.03 solo tiene la otra altura: no se rellena
    assert lineas(a)[0]["v"] == 61.385 and lineas(a)[0]["csv"] is None
    b = evolucion.construir(filas(), csv, elemento=abajo)
    assert [m["n"] for m in b["muestreos"]] == [3, 5, 7]
    assert lineas(b)[0]["v"] == 60.723 and lineas(b)[1]["csv"]["linea"] == 92 and lineas(b)[1]["v"] == 61.27


def test_calificadores_de_excel_y_csv():
    from evolucion import calificadores, compatibles

    assert calificadores("N310.1 Thickness 1,5 (Max-Value / 36 Points)") == {"extremo": "max"}
    assert calificadores("N730 Roundness 0,1 ø29,2 (Min-Zone) in height 4mm") == {"posicion": frozenset({4.0})}
    assert compatibles(calificadores("gg h=-4.5 mm"), calificadores("N550 ø61,4 (GG) X=-4,5"))
    assert not compatibles(calificadores("gg h=-8.5 mm a la punta"), calificadores("N550 ø61,4 (GG) X=-4,5"))
    assert not compatibles(calificadores("gn"), calificadores("N720 ø29,2 (GG) in height 4mm"))
    assert compatibles(calificadores(""), calificadores("POINT 1 -> 1.35-0.05 MIN/MAX"))  # sin datos no hay contradicción
    # 3212: el bloque trae las dos medidas (GX y LP máximo); «1MIN» pegado no lo convierte en un máximo.
    assert calificadores("N170 BOLT 1MIN/MAX H=1.5mm") == {"posicion": frozenset({1.5})}
    assert compatibles(calificadores("min ø1 h= -1.5"), calificadores("N170 BOLT 1MIN/MAX H=1.5mm"))


# ---------------------------------------------------------------- pestaña Errores

def test_cada_hallazgo_esta_clasificado_y_ninguna_incidencia_se_pierde():
    """Todo hallazgo es una incidencia (I-xxx), una nota técnica (pestaña Revisión) o de un tipo que no es error.

    Los que no son errores no se muestran en el visor desde el 10/11/2026: siguen en conocimiento/. Un tipo nuevo
    sin clasificar hace fallar el test, para decidir dónde va.
    """
    import errores

    clasificados = errores.NO_SON_ERRORES | set(errores.TECNICOS)
    for x in datos.hallazgos():
        assert x["id"].startswith("I-") or x["tipo"] in clasificados, x["id"]
    inc = errores.incidencias()
    assert len(inc) == sum(x["id"].startswith("I-") for x in datos.hallazgos())
    vistas = {i["id"] for c in errores.catalogo() for i in errores.propias(c)} | {i["id"] for i in errores.generales()["incidencias"]}
    assert vistas == {i["id"] for i in inc}  # cada incidencia sale en una pieza o en «Generales y otras referencias»


def test_titulos_de_incongruencias_y_estados_sin_dar_nada_por_comprobado():
    import errores

    assert errores.transversales() == {f"I-00{n}" for n in range(1, 9)}  # la sección «Transversales», no un umbral
    for i in errores.incidencias():
        assert i["id"] in errores.titulos() and i["titulo"] == errores.titulos()[i["id"]]
        assert i["estado"] in ("Duda", "Pendiente de aclarar", "Explicación posible · sin confirmar", "Resuelta", "Corregida")
        # Una explicación posible no está confirmada: sigue pendiente (revisión del 09/11/2026).
        assert i["pendiente"] == (i["estado"] in ("Duda", "Pendiente de aclarar", "Explicación posible · sin confirmar"))
    explicables = [i["id"] for i in errores.incidencias() if i["estado"].startswith("Explicación posible")]
    assert {"I-002", "I-201"} <= set(explicables) and len(explicables) == 9
    i208 = next(i for i in errores.incidencias() if i["id"] == "I-208")
    assert i208["estado"] == "Pendiente de aclarar" and i208["graficas"] == [{"pieza": "3197", "cota": "120"}]
    assert {e["fichero"] for e in i208["evidencia"]} == {"3197-00_intern.07.xls", "3197c1.csv", "3197.csv"}
    assert errores.estado({"tipo": "pregunta", "estado": "abierta"}) == "Duda"


def test_las_generales_de_una_pieza_son_solo_las_que_le_afectan():
    import errores

    for codigo in errores.catalogo():
        g = errores.generales(codigo)["incidencias"]
        assert all(i["general"] and codigo in i["piezas"] for i in g)
        r = errores.resumen_pieza(codigo)
        assert r["generales"] == len(g) and r["generales_pendientes"] == sum(i["pendiente"] for i in g)
        p = errores.propias(codigo)
        assert not any(i["general"] for i in p) and r["propias_pendientes"] == sum(i["pendiente"] for i in p)
    assert [i["id"] for i in errores.generales("3197")["incidencias"]] == ["I-008"]


def test_revision_recibe_los_casos_y_las_notas_tecnicas():
    import errores

    t = errores.tecnicos()
    assert len(t["casos"]) == len(datos.casos())
    assert {x["tipo"] for x in t["notas"]} <= set(errores.TECNICOS.values())


def test_api_de_errores():
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    import app

    c = TestClient(app.app)
    lista = c.get("/api/errores").json()
    assert len(lista["piezas"]) == len(datos.piezas()) and lista["otras"]["total"] >= 8
    assert c.get("/api/errores/pieza/3197").json()["propias"] == len([x for x in datos.hallazgos() if x["id"].startswith("I-")
                                                                        and "3197" in datos.piezas_de(x["pieza"]) and x["id"] not in {f"I-00{n}" for n in range(1, 9)}])
    assert c.get("/api/errores/pieza/9999").status_code == 404
    assert [i["id"] for i in c.get("/api/errores/generales?pieza=3197").json()["incidencias"]] == ["I-008"]
    assert len(c.get("/api/revision/referencias").json()["casos"]) == len(datos.casos())
    # Tras cambiar la API, el navegador no puede quedarse con el app.js viejo.
    assert c.get("/static/app.js").headers["cache-control"] == "no-cache"
    assert c.get("/api/pieza/3051/ficheros").json()["total"]["n"] > 0 and c.get("/api/pieza/9999/ficheros").status_code == 404
    inicio = c.get("/").text
    assert '"/static/app.js?v=' in inicio and '"/static/app.css?v=' in inicio and '"/static/app.js"' not in inicio
