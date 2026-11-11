"""Casos sintéticos para identidad y consultas completas."""
import argparse
import contextlib
import io
import json
import sqlite3
import sys
import unittest

from consultar import cmd_buscar
from identidad_piezas import clasificar, valido
from medidas_cmm import leer_csv
from conocimiento_feature import exportar, validar


class RevisionTests(unittest.TestCase):
    def test_caso_rechaza_valor_correcto_con_estado_o_marca_equivocados(self):
        from verificar_aceptacion import comprobar_salida_caso
        caso={'id':'CR-test','esperado_backend':{'estado':'medicion','marcas_prohibidas':['identidad_sin_confirmar']}}
        self.assertTrue(comprobar_salida_caso(caso,{'value':22.243,'provenance_state':'sin_confirmar','flags':['identidad_sin_confirmar']}))
        caso['esperado_backend']={'estado':'sin_confirmar','marcas':['posible_copia_de_generador']}
        self.assertTrue(comprobar_salida_caso(caso,{'provenance_state':'sin_confirmar','flags':[]}))
        self.assertEqual(comprobar_salida_caso(caso,{'provenance_state':'sin_confirmar','flags':['posible_copia_de_generador']}),[])

    def test_csv_detecta_intercambio_de_muestras_de_la_misma_cavidad(self):
        from verificar_aceptacion import comprobar_csv
        data=b'N10;;;;;;C1.1;C1.2\n;GX;;4;0.1;-0.1;3.95;4.02\n'
        row=dict(line=2,_wide=True,_cavity='c1',_variant='1',value=3.95,nominal=4,tol_sup=0.1,tol_inf=-0.1)
        self.assertEqual(comprobar_csv(data,[row]),[])
        self.assertTrue(comprobar_csv(data,[{**row,'value':4.02}]))

    def test_balance_rechaza_valores_desaparecidos_o_adicionales_sin_contraste(self):
        from verificar_aceptacion import validar_balance
        hoja=dict(hoja='DR',referencia=3,salida=3,coinciden=2,no_leidas=1,discrepantes=0,adicionales=1,
                  medicion=2,generado=1,sin_confirmar=0,adicionales_medicion=0)
        self.assertEqual(validar_balance({'id':1,'hojas':[hoja]}),[])
        self.assertTrue(validar_balance({'id':1,'hojas':[{**hoja,'no_leidas':0}]}))
        self.assertTrue(validar_balance({'id':1,'hojas':[{**hoja,'adicionales_medicion':1}]}))

    def test_referencia_independiente_conserva_coordenadas_en_copia_cliente(self):
        from auditar_ingesta import referencia_cliente
        grid=[['Nr','Nominal','Tol +','Tol-','Nr.1','Nr.2'],[10,4,0.1,-0.1,3.95,3.96]]
        r=referencia_cliente('CAV.1 (2)',grid,{(2,6)})
        self.assertEqual([(m[0],m[1],m[8]) for m in r['medidas']],[(2,5,3.95),(2,6,3.96)])
        self.assertEqual(r['medidas'][1][9],'aleatoria')
        repetidas=[['Nr','Nominal','Tol +','Tol-','CAV.1_1 1','CAV.1_1 2'],[1604,17.25,0.05,-0.05,17.226,17.224]]
        r=referencia_cliente('DR variabilidad',repetidas,set())
        self.assertEqual([(m[1],m[7],m[8]) for m in r['medidas']],[(5,'c1.1.1',17.226),(6,'c1.1.2',17.224)])

    def test_exportacion_documental_no_atribuye_validacion_corporativa(self):
        r=dict(id='W-test',tipo='warning',titulo='Prueba',afirmacion='Texto',aplica_a={'ambito':'pieza','feature':'Clips','piezas':['1234']},cotas=[],validacion='revisado_documentalmente',fuente_validacion={'responsable':'Codex'},evidencia=[{'ruta':'prueba','localizador':'p1'}])
        self.assertEqual(exportar([r])['FeatureNote'],[])
        salida=exportar([r],revisados=True)
        self.assertEqual(salida['FeatureNote'][0]['validacion'],'revisado_documentalmente')
        self.assertFalse(salida['carga_automatica'])

    def test_codigo_del_bloque_principal_no_del_nr_de_una_comparativa(self):
        from lector_dr import leer_hoja
        celdas={(1,10):'Nr',(2,1):'Nr',(2,2):'Nominal',(2,3):'Tol +',(2,4):'Tol-',(2,5):'CAV.1',
                (3,1):'215',(3,2):'0.1',(3,3):'0',(3,4):'-0.1',(3,5):'0.65',(3,10):'206'}
        r=leer_hoja('DR',celdas,set())
        self.assertEqual(r['columnas']['codigo'],1)
        self.assertEqual(r['medidas'][0][2],'215')

    def test_signo_cmm_con_nominal_positivo_y_negativo_conserva_original(self):
        for nominal, medido in [(31, -30.99), (-31, 31.001)]:
            csv = f"DIAGNOSTICO B2\n32;Posición Z;;{nominal};0.1;-0.1;{medido};99;99\n".encode("cp1252")
            row = leer_csv(csv)[0]
            self.assertEqual(row["valor"], -medido)
            self.assertEqual(row["valor_original"], medido)
            self.assertAlmostEqual(row["desviacion"], -medido - nominal)
            self.assertEqual(row["fuera"], 0)

    def test_n170_identidad_por_id_cmm_no_por_rotulo_erroneo(self):
        datos = b"N170 BOLT 1 H=5.0\n16;Diametro;;4;0;-0.1;3.98;-0.02;\n;LP(2);;4;0;-0.1;4.02;0.02;0.02\n"
        rows = leer_csv(datos)
        self.assertEqual([(r["bolt"],r["altura"],r["evaluacion"]) for r in rows], [("B2",5.0,"GX"),("B2",5.0,"LP_max")])

    def test_exportacion_no_promueve_borradores_ni_inventa_validacion(self):
        r = dict(id="W-test", tipo="warning", titulo="Prueba", afirmacion="Texto", aplica_a={"ambito":"pieza","feature":"Clips","piezas":["1234"]}, cotas=[], validacion="borrador", fuente_validacion=None, evidencia=[{"ruta":"prueba","localizador":"p1"}])
        self.assertEqual(exportar([r])["FeatureNote"], [])
        self.assertEqual(exportar([r], True)["FeatureNote"][0]["note"]["kind"], "warning")
        self.assertTrue(validar({**r, "validacion":"validado_por_INTEPLAST"}))
    def test_plantilla_heredada_no_identifica_la_pieza_de_la_carpeta(self):
        self.assertEqual(clasificar("3288", {"itp_ref": "732470000", "ppap_ref": "3247-00_int.01", "part_no": "509131"}, {})[0], "heredada")

    def test_fecha_en_numero_de_pieza_detecta_desplazamiento(self):
        self.assertFalse(valido("11/12/2018", "part_no"))
        self.assertEqual(clasificar("3288", {"itp_ref": "0", "ppap_ref": "DB", "part_no": "11/12/2018"}, {})[0], "desplazada")

    def test_errata_ppap_no_descarta_dos_identificadores_coherentes(self):
        meta = {"itp_ref": "732180000", "ppap_ref": "3281-00_int.04", "part_name": "Bearing plate", "part_no": "654695200B"}
        state, warnings = clasificar("3218", meta, {"part_name": {"Bearing plate"}, "part_no": {"654695200B"}})
        self.assertEqual(state, "propia")
        self.assertTrue(warnings)
        self.assertEqual(clasificar("3218", {"ppap_ref": "3281-00_int.04"}, {})[0], "conflicto")

    def test_busqueda_avisa_total_con_los_mismos_filtros(self):
        with sqlite3.connect(":memory:") as con:
            con.executescript("CREATE TABLE documento(id INTEGER PRIMARY KEY,ruta TEXT,feature TEXT); CREATE TABLE elemento(id INTEGER PRIMARY KEY,documento_id INTEGER,localizador TEXT); CREATE VIRTUAL TABLE elemento_fts USING fts5(texto);")
            for n in range(1, 55):
                con.execute("INSERT INTO documento VALUES (?,?,?)", (n, f"{n}.txt", "Clips"))
                con.execute("INSERT INTO elemento VALUES (?,?,?)", (n, n, "L1"))
                con.execute("INSERT INTO elemento_fts(rowid,texto) VALUES (?,?)", (n, "ventings"))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                cmd_buscar(con, argparse.Namespace(consulta="venting*", feature="Clips", n=30))
            self.assertIn("30 de 54", out.getvalue())
            self.assertIn("truncados", out.getvalue())
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                cmd_buscar(con, argparse.Namespace(consulta="venting*", feature="Otra", n=30))
            self.assertIn("0 de 0", out.getvalue())

    def test_comparar_derivadas_detecta_campos_y_no_el_id_de_elemento(self):
        """Auditoría del 11/11/2026: comparar filas y campos, no recuentos; `elemento.id` se renumera al reextraer."""
        import tempfile
        from pathlib import Path

        from comparar_derivadas import tablas

        with tempfile.TemporaryDirectory() as d:
            rutas = []
            for nombre, valor, ident in (("a.sqlite", 1.5, 10), ("b.sqlite", 1.6, 99)):
                ruta = str(Path(d) / nombre)
                con = sqlite3.connect(ruta)
                con.executescript("CREATE TABLE perfil_ppap (documento_id INTEGER, hoja TEXT, nok INTEGER);"
                                  "CREATE TABLE elemento (id INTEGER PRIMARY KEY, documento_id INTEGER, texto TEXT);")
                con.execute("INSERT INTO perfil_ppap VALUES (1, 'DR', ?)", (valor,))
                con.execute("INSERT INTO elemento VALUES (?, 1, 'igual')", (ident,))
                con.commit()
                con.close()
                rutas.append(ruta)
            r = tablas(*rutas, ["perfil_ppap", "elemento"])
        self.assertEqual(r["perfil_ppap"]["filas_actual"], r["perfil_ppap"]["filas_nueva"])  # mismo recuento...
        self.assertEqual(r["perfil_ppap"]["campos_que_cambian"], {"nok": 1})  # ...pero un campo distinto
        self.assertEqual((r["elemento"]["distintas_actual"], r["elemento"]["distintas_nueva"]), (0, 0))

    def test_contraste_m3_compara_por_cota_cavidad_y_muestra_aunque_se_desplacen_las_filas(self):
        """P-2/P-5 (11/11/2026): la clave no depende de la fila; el número de muestra sí del orden dentro de la hoja."""
        from contraste_m3 import claves, letra

        a = claves([("DR", 14, 9, "101", "c1", 1.5, None), ("DR", 15, 9, "101", "c1", 1.6, None), ("DR", 16, 9, "102", "c1", 2.0, "cero")])
        b = claves([("DR", 17, 9, "101", "c1", 1.5, None), ("DR", 18, 9, "101", "c1", 1.6, None)])  # tres filas más abajo
        self.assertEqual(a[("101", "c1", 1)][:3], (15, 9, 1.6))
        self.assertEqual({k: v[2] for k, v in a.items() if k in b}, {k: v[2] for k, v in b.items()})
        self.assertEqual(a[("102", "c1", 0)][3], "cero")  # la marca viaja con la clave para poder excluirla
        self.assertEqual([letra(1), letra(26), letra(27), letra(52)], ["A", "Z", "AA", "AZ"])

    @staticmethod
    def _evaluar(filas_a, filas_b):
        """filas_*: [(fila, cavidad, valor, marca)] de la cota '1' (una muestra por fila y cavidad)."""
        from contraste_m3 import evaluar

        def hoja(filas):
            return {(f"f{fila}", cav, 0): (fila, 8 + int(cav[1:]), v, m) for fila, cav, v, m in filas}

        a, b = hoja(filas_a), hoja(filas_b)
        valores_a = {(f, c): v for f, c, v, _ in a.values()}
        valores_b = {(f, c): v for f, c, v, _ in b.values()}
        return evaluar(a, b, lambda f, c: valores_a.get((f, c)), lambda f, c: valores_b.get((f, c)))

    def test_contraste_m3_vale_un_bloque_que_cumple_aunque_el_mas_largo_no(self):
        """Revisión del 11/11/2026 (3186 `intern.16`): el bloque más largo, de valores redondos, no justifica nada."""
        redondas = [(f, c, 1.5, None) for f in range(10, 16) for c in ("c1", "c2")]  # 6 filas iguales sin decimales
        rotura = [(16, "c1", 2.0, None)]
        con_decimales = [(f, c, 0.1234 + f / 1000, None) for f in range(17, 22) for c in ("c1", "c2")]  # 5 filas, 10 valores
        distintas = [(f, c, 5.0, None) for f in range(30, 35) for c in ("c1", "c2")]
        a = redondas + rotura + con_decimales + distintas
        b = redondas + [(16, "c1", 3.0, None)] + con_decimales + [(f, c, 6.0, m) for f, c, _, m in distintas]
        r = self._evaluar(a, b)
        self.assertEqual(r["clase"], "repetición confirmada (parcial)")
        self.assertEqual((r["bloque_valido"]["desde"], r["bloque_valido"]["hasta"], r["bloque_valido"]["con_decimales"]), (17, 21, 10))
        self.assertEqual((r["bloque_mas_largo"]["filas"], r["bloque_mas_largo"]["con_decimales"]), (6, 0))

    def test_contraste_m3_una_fila_con_medidas_sin_pareja_rompe_el_bloque(self):
        """Revisión del 11/11/2026 (3212 `intern.02`, fila 142: 4 de 8 medidas con pareja): la fila no cuenta como igual."""
        a = [(f, c, 0.111 + f / 1000, None) for f in range(10, 17) for c in ("c1", "c2")]
        b = [x for x in a if (x[0], x[1]) != (13, "c2")]  # la fila 13 solo tiene pareja en c1
        r = self._evaluar(a, b)
        self.assertEqual((r["sin_pareja"], r["comparadas"], r["iguales"]), (1, 13, 13))
        self.assertIsNone(r["bloque_valido"])  # antes: un bloque de 7 filas
        self.assertEqual(r["bloque_mas_largo"]["filas"], 3)
        self.assertEqual(r["clase"], "pendiente")

    def test_contraste_m3_los_decimales_se_cuentan_dentro_del_bloque(self):
        """Revisión del 11/11/2026: coincidencias con decimales fuera del bloque no lo hacen válido."""
        bloque = [(f, c, 2.0, None) for f in range(10, 16) for c in ("c1", "c2")]  # 6 filas, sin decimales
        sueltas_a = [(f, "c1", 0.5 + f / 1000, None) for f in range(30, 45)] + [(f, "c2", 9.0, None) for f in range(30, 45)]
        sueltas_b = [(f, "c1", 0.5 + f / 1000, None) for f in range(30, 45)] + [(f, "c2", 8.0, None) for f in range(30, 45)]
        r = self._evaluar(bloque + sueltas_a, bloque + sueltas_b)
        self.assertIsNone(r["bloque_valido"])  # antes: 15 valores con decimales en la hoja bastaban
        self.assertEqual(r["clase"], "pendiente")

    def test_contraste_m3_recuentos_separan_excluidas_sin_pareja_y_comparadas(self):
        a = [(10, "c1", 0.0, "cero"), (10, "c2", 0.5, "aleatoria"), (11, "c1", 1.234, None), (11, "c2", 1.5, None), (12, "c1", 2.5, None)]
        b = [(10, "c1", 0.0, "cero"), (10, "c2", 0.7, "aleatoria"), (11, "c1", 1.234, None), (11, "c2", 1.6, None)]
        r = self._evaluar(a, b)
        self.assertEqual([r[k] for k in ("total", "excluidas", "sin_pareja", "comparadas", "iguales")], [5, 2, 1, 2, 1])

    def _carpetas(self, actual: dict, nueva: dict):
        """Dos carpetas de aceptación con ficheros {nombre: [filas]}; devuelve (directorio temporal, actual, nueva)."""
        import tempfile
        from pathlib import Path

        d = tempfile.TemporaryDirectory()
        rutas = []
        for nombre, ficheros in (("actual", actual), ("nueva", nueva)):
            carpeta = Path(d.name) / nombre
            carpeta.mkdir()
            for f, filas in ficheros.items():
                (carpeta / f).write_text("".join(json.dumps(x) + "\n" for x in filas), encoding="utf-8")
            rutas.append(str(carpeta))
        return d, *rutas

    def _comparar(self, actual: dict, nueva: dict):
        """Detección (`aceptacion`) y resultado del comando (`main`, código de salida)."""
        from comparar_derivadas import aceptacion, main

        d, a, b = self._carpetas(actual, nueva)
        with d, contextlib.redirect_stdout(io.StringIO()):
            return aceptacion(a, b), main(["aceptacion", a, b])

    def test_comparar_aceptacion_ve_ficheros_de_una_sola_carpeta(self):
        """11/11/2026: solo recorría los ficheros de la carpeta actual; uno añadido en la nueva no se veía."""
        base = {"p.jsonl": [{"id": 1, "x": 1}]}
        r, rc = self._comparar(base, base)
        self.assertEqual(rc, 0)
        self.assertEqual((r["ficheros_solo_actual"], r["ficheros_solo_nueva"]), ([], []))
        r, rc = self._comparar(base, {**base, "vacio.jsonl": []})  # aunque esté vacío
        self.assertEqual((r["ficheros_solo_nueva"], rc), (["vacio.jsonl"], 1))
        r, rc = self._comparar({**base, "q.jsonl": [{"id": 9}]}, base)
        self.assertEqual((r["ficheros_solo_actual"], r["solo_actual"], rc), (["q.jsonl"], 1, 1))

    def test_comparar_aceptacion_ve_ids_duplicados(self):
        """11/11/2026: un diccionario por `id` ocultaba las filas repetidas, en un fichero o entre ficheros."""
        base = {"p.jsonl": [{"id": 1, "x": 1}, {"id": 2, "x": 2}]}
        r, rc = self._comparar(base, {"p.jsonl": base["p.jsonl"] + [{"id": 2, "x": 2}]})  # en el mismo fichero
        self.assertEqual((r["duplicados_nueva"], r["duplicados_actual"], rc), ({"2": 2}, {}, 1))
        entre = {"p.jsonl": [{"id": 1}], "q.jsonl": [{"id": 1}]}  # entre ficheros, igual en las dos carpetas
        r, rc = self._comparar(entre, entre)
        self.assertEqual((r["con_cambios"], r["solo_nueva"]), (0, 0))  # fichero a fichero no cambia nada...
        self.assertEqual((r["duplicados_actual"], r["duplicados_nueva"], rc), ({"1": 2}, {"1": 2}, 1))  # ...pero se ve

    def test_comparar_aceptacion_codigo_de_salida_del_proceso(self):
        import subprocess
        from pathlib import Path

        script = str(Path(__file__).with_name("comparar_derivadas.py"))
        for nueva, esperado in (({"p.jsonl": [{"id": 1}]}, 0), ({"p.jsonl": [{"id": 1}], "n.jsonl": []}, 1)):
            d, a, b = self._carpetas({"p.jsonl": [{"id": 1}]}, nueva)
            with d:
                proceso = subprocess.run([sys.executable, "-B", script, "aceptacion", a, b], capture_output=True)
            self.assertEqual(proceso.returncode, esperado, proceso.stderr)


if __name__ == "__main__":
    unittest.main()
