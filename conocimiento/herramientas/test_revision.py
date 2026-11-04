"""Casos sintéticos para identidad y consultas completas."""
import argparse
import contextlib
import io
import sqlite3
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


if __name__ == "__main__":
    unittest.main()
