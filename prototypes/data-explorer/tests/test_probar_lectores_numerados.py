"""Medida de los lectores numerados: muestra reproducible, contraste con informes y recuentos. Sin ficheros del cliente."""

import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import probar_lectores_numerados as medida


def lectura(t, p=1, x=.5, y=.5, via="No."):
    return {"p": p, "t": t, "s": .9, "via": via, "x": x, "y": y, "w": .01, "h": .005}


def token(texto, p_x=.3, p_y=.4):
    q = [[p_x, p_y], [p_x + .02, p_y], [p_x + .02, p_y + .005], [p_x, p_y + .005]]
    return {"texto": texto, "s": .9, "q": q}


def leidas(lecturas_2820=None, recuadros_3205=None, pdf="pdf-a"):
    """Lecturas mínimas de los 8 planos de la medida (4 numerados y 4 controles)."""
    salida = {}
    for doc in (*medida.POSITIVOS, *medida.NEGATIVOS, *medida.FORZADOS):
        salida[doc] = {"doc": doc, "codigo": str(doc), "nombre": f"plano {doc}", "identidad": {"codigo": 1},
                       "firma": {"sha256": f"{pdf}-{doc}"}, "lecturas": [],
                       "detalle": {"marcas": [], "recuadros": [], "ocr": []}}
    salida[1]["lecturas"] = lecturas_2820 or []
    salida[1631]["detalle"]["recuadros"] = recuadros_3205 or []
    return salida


def sin_cotas(_codigo):
    return set()


def decide(revision, clave, **valores):
    revision["decisiones"][clave].update(valores)


class MuestraTests(unittest.TestCase):
    def test_la_muestra_se_repite_con_la_misma_semilla_y_cambia_con_otra(self):
        a = medida.elige(300, 40, 20261110, "lecturas-582")
        self.assertEqual(a, medida.elige(300, 40, 20261110, "lecturas-582"))
        self.assertEqual(len(set(a)), 40)
        self.assertNotEqual(a, medida.elige(300, 40, 7, "lecturas-582"))
        self.assertNotEqual(a, medida.elige(300, 40, 20261110, "lecturas-873"))  # cada plano, su muestra

    def test_con_pocas_mas_que_la_muestra_se_revisan_todas(self):
        self.assertEqual(medida.elige(45, 40, 1, "x"), list(range(45)))

    def test_cota_del_informe_no_encontrada_compara_por_la_base_de_la_cota(self):
        leidas_ = [lectura("120"), lectura("45.1"), lectura("7")]
        self.assertEqual(medida.no_encontradas({"120", "45", "7", "9", "300"}, leidas_), ["9", "300"])

    def test_candidatos_solo_con_el_numero_suelto_y_sin_repetir_el_sitio(self):
        ocr = [{"pagina": 2, "tokens": [token("No.123"), token("No 123", .3005, .4002),  # mismo sitio, otra tesela
                                         token("1234", .6), token("12.3", .7), token("0.123", .8), token("123±0.1", .1, .1)]}]
        sitios = medida.candidatos(ocr, "123")
        self.assertEqual([(s["p"], s["texto"]) for s in sitios], [(2, "No.123"), (2, "123±0.1")])
        self.assertAlmostEqual(sitios[0]["x"], .31)

    def test_plan_separa_lecturas_controles_y_contraste(self):
        datos = leidas(recuadros_3205=[lectura("5", via="recuadro")] * 3)
        datos[582]["lecturas"] = [lectura(str(100 + i), x=i / 60) for i in range(55)]
        datos[582]["detalle"]["ocr"] = [{"pagina": 1, "tokens": [token("No.999 R2")]}]
        plan = medida.plan_de_muestra(datos, 3, lambda codigo: {"100", "101", "999"} if codigo == "582" else set())
        tipos = [i["tipo"] for i in plan["items"]]
        self.assertEqual(tipos.count("lectura"), 40)
        self.assertEqual(tipos.count("negativo"), 3)  # pocas detecciones: se revisan todas
        self.assertEqual(plan["contraste"]["582"]["no_encontradas"], ["999"])
        self.assertEqual([i["id"] for i in plan["items"] if i["tipo"] == "candidato"], ["C582-999-0"])
        self.assertEqual(plan["detecciones_negativas"]["1631"], 3)
        self.assertTrue(all(i["huella"] for i in plan["items"] if i["tipo"] in ("lectura", "negativo")))


class VigenciaTests(unittest.TestCase):
    """Una decisión vale para lo que se revisó: el mismo PDF y la misma lectura, no el mismo identificador."""

    def revisada(self, datos):
        plan = medida.plan_de_muestra(datos, 1, sin_cotas)
        revision = medida.concilia(plan, {})
        decide(revision, "L1-0", numero="bien", ubicacion="bien", visto="210")
        return plan, revision

    def test_una_decision_no_pasa_a_otra_lectura_con_el_mismo_identificador(self):
        plan, revision = self.revisada(leidas([lectura("210", via="[]")]))
        cambiada = medida.plan_de_muestra(leidas([lectura("999", via="[]")]), 1, sin_cotas)
        # Sin conciliar, el informe no la cuenta: la huella no es la de la lectura 999.
        pagina = medida.resume(cambiada, revision, leidas([lectura("999", via="[]")]))["planos"]["1"]["paginas"][1]
        self.assertEqual((pagina["numero"], pagina["ambas_bien"]), ({"sin revisar": 1}, 0))
        # Al regenerar la muestra, la decisión pasa a «invalidadas» y su sitio queda vacío.
        conciliada = medida.concilia(cambiada, revision)
        self.assertIsNone(conciliada["decisiones"]["L1-0"]["numero"])
        self.assertEqual([(x["clave"], x["visto"]) for x in conciliada["invalidadas"]], [("L1-0", "210")])

    def test_tambien_si_solo_cambia_el_pdf(self):
        plan, revision = self.revisada(leidas([lectura("210", via="[]")]))
        otro_pdf = medida.plan_de_muestra(leidas([lectura("210", via="[]")], pdf="pdf-b"), 1, sin_cotas)
        self.assertIsNone(medida.concilia(otro_pdf, revision)["decisiones"]["L1-0"]["numero"])

    def test_con_la_misma_lectura_la_decision_se_conserva(self):
        plan, revision = self.revisada(leidas([lectura("210", via="[]")]))
        otra_vez = medida.concilia(medida.plan_de_muestra(leidas([lectura("210", via="[]")]), 1, sin_cotas), revision)
        self.assertEqual(otra_vez["decisiones"]["L1-0"]["numero"], "bien")
        self.assertEqual(otra_vez["invalidadas"], [])

    def test_una_omision_del_barrido_se_invalida_si_cambia_lo_que_ofrece_el_lector(self):
        plan, revision = self.revisada(leidas([lectura("210", via="[]")]))
        revision["omisiones"].append({"doc": 1, "p": 1, "x": .2, "y": .3, "numero": "215",
                                      "huella": plan["huella_omisiones"]["1"]})
        self.assertEqual(len(medida.resume(plan, revision, leidas([lectura("210", via="[]")]))["planos"]["1"]["omisiones_confirmadas"]), 1)
        nuevas = leidas([lectura("210", via="[]"), lectura("215", via="[]", x=.2, y=.3)])
        cambiada = medida.plan_de_muestra(nuevas, 1, sin_cotas)
        self.assertEqual(medida.resume(cambiada, revision, nuevas)["planos"]["1"]["omisiones_confirmadas"], [])
        self.assertEqual(medida.concilia(cambiada, revision)["omisiones"], [])

    def test_la_cache_de_lecturas_mira_el_codigo_y_el_pdf(self):
        guardado = {"identidad": {"codigo": 1}, "firma": {"sha256": "a", "version": 1}}
        self.assertTrue(medida.al_dia(guardado, {"codigo": 1}, {"sha256": "a", "version": 1}))
        self.assertFalse(medida.al_dia(guardado, {"codigo": 1}, {"sha256": "b", "version": 1}))  # otro PDF
        self.assertFalse(medida.al_dia(guardado, {"codigo": 2}, {"sha256": "a", "version": 1}))  # otro código
        self.assertFalse(medida.al_dia(guardado, {"codigo": 1}, None))  # no se puede comprobar el PDF
        self.assertFalse(medida.al_dia(None, {"codigo": 1}, {"sha256": "a", "version": 1}))

    def carpeta_revisada(self, datos):
        """Lecturas, muestra y revisión en una carpeta temporal, como las deja la fase «muestra»."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        carpeta = Path(tmp.name)
        (carpeta / "lecturas").mkdir()
        for doc, r in datos.items():
            (carpeta / "lecturas" / f"{doc}.json").write_text(json.dumps(r), encoding="utf-8")
        plan = medida.plan_de_muestra(datos, 1, sin_cotas)
        revision = medida.concilia(plan, {})
        decide(revision, "N1631-0", resultado="falso", nota="cota básica 12.02")
        (carpeta / "muestra.json").write_text(json.dumps(plan), encoding="utf-8")
        (carpeta / "revision.json").write_text(json.dumps(revision), encoding="utf-8")
        firmas = {d: (r["firma"], "local") for d, r in datos.items()}  # los PDF no han cambiado
        parche = mock.patch.object(medida, "firma_actual", lambda d: firmas[d])
        parche.start()
        self.addCleanup(parche.stop)
        return carpeta

    def test_el_informe_se_detiene_si_cambia_una_deteccion_de_un_control(self):
        datos = leidas(recuadros_3205=[lectura("12.02", via="recuadro")])
        carpeta = self.carpeta_revisada(datos)
        with contextlib.redirect_stdout(io.StringIO()):
            medida.informe(carpeta)  # sin cambios, el informe sale
        resumen = json.loads((carpeta / "informe.json").read_text(encoding="utf-8"))
        self.assertEqual(resumen["controles"]["1631"]["resultado"], {"falso": 1})
        datos[1631]["detalle"]["recuadros"][0]["t"] = "999"  # en un control, lo revisado son las detecciones
        (carpeta / "lecturas" / "1631.json").write_text(json.dumps(datos[1631]), encoding="utf-8")
        with self.assertRaises(SystemExit) as salida:
            medida.informe(carpeta)
        self.assertIn("1631", str(salida.exception.code))

    def test_el_informe_rechaza_un_pdf_distinto_del_de_la_muestra(self):
        plan = medida.plan_de_muestra(leidas(), 1, sin_cotas)
        firmas = {d: {"sha256": plan["entrada"][str(d)]["pdf"]} for d in (1, 582)}
        self.assertEqual(medida.pdf_cambiado(plan, firmas), [])
        self.assertEqual(medida.pdf_cambiado(plan, {**firmas, 582: {"sha256": "otro"}, 873: None}), [582, 873])


class InformeTests(unittest.TestCase):
    def test_numero_y_ubicacion_por_separado_y_lo_no_revisado_aparte(self):
        datos = leidas([lectura("210", via="[]"), lectura("211", via="[]"), lectura("212", via="[]")])
        plan = medida.plan_de_muestra(datos, 1, sin_cotas)
        revision = medida.concilia(plan, {})
        decide(revision, "L1-0", numero="bien", ubicacion="bien", visto="210")
        decide(revision, "L1-1", numero="bien", ubicacion="mal", visto="211", nota="en una tabla")
        revision["omisiones"].append({"doc": 1, "p": 1, "x": .2, "y": .3, "numero": "215", "nota": "marca sin caja",
                                      "huella": plan["huella_omisiones"]["1"]})
        r = medida.resume(plan, revision, datos)
        pagina = r["planos"]["1"]["paginas"][1]
        self.assertEqual(pagina["numero"], {"bien": 2, "sin revisar": 1})
        self.assertEqual(pagina["ubicacion"], {"bien": 1, "mal": 1, "sin revisar": 1})
        self.assertEqual(pagina["ambas_bien"], 1)
        self.assertEqual([f["id"] for f in r["planos"]["1"]["fallos"]], ["L1-1"])
        self.assertEqual(r["planos"]["1"]["omisiones_confirmadas"][0]["numero"], "215")

    def test_solo_la_cota_con_su_marca_vista_pasa_a_omision(self):
        datos = leidas()
        plan = medida.plan_de_muestra(datos, 1, lambda codigo: {"300", "301"} if codigo == "582" else set())
        revision = medida.concilia(plan, {})
        decide(revision, "C582-300", resultado="omision_confirmada", evidencia="C582-300-1")
        decide(revision, "C582-301", resultado="no_encontrada")
        r = medida.resume(plan, revision, datos)["planos"]["582"]
        self.assertEqual(r["contraste"], {"300": "omision_confirmada", "301": "no_encontrada"})
        self.assertEqual([o["cota"] for o in r["omisiones_confirmadas"]], ["300"])

    def test_en_los_controles_las_seleccionadas_sin_decision_siguen_pendientes(self):
        datos = leidas(recuadros_3205=[lectura(str(n), via="recuadro") for n in (5, 6, 7)])
        plan = medida.plan_de_muestra(datos, 1, sin_cotas)
        revision = medida.concilia(plan, {})
        decide(revision, "N1631-0", resultado="falso", nota="cota básica")
        control = medida.resume(plan, revision, datos)["controles"]["1631"]
        self.assertEqual((control["detecciones"], control["seleccionadas"], control["revisadas"], control["pendientes"]),
                         (3, 3, 1, 2))
        self.assertEqual(control["resultado"], {"falso": 1})

    def test_una_decision_fuera_de_las_categorias_es_un_error(self):
        datos = leidas([lectura("210", via="[]")])
        plan = medida.plan_de_muestra(datos, 1, lambda codigo: {"301"} if codigo == "582" else set())
        revision = medida.concilia(plan, {})
        decide(revision, "L1-0", numero="regular")
        decide(revision, "C582-301", resultado="omision")
        self.assertEqual(len(medida.valida(plan, copy.deepcopy(revision))), 2)


class RecorteTests(unittest.TestCase):
    def test_el_recorte_marca_la_caja_dentro_de_la_pagina(self):
        gris = np.full((1000, 2000), 255, np.uint8)
        img = medida.recorte(gris, {"x": .999, "y": .001, "w": .01, "h": .01})  # en la esquina: no se sale
        self.assertEqual(img.ndim, 3)
        self.assertTrue((img[..., 2] > img[..., 1]).any())  # hay rojo


if __name__ == "__main__":
    unittest.main()
