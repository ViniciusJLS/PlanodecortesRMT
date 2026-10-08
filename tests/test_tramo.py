import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import openpyxl
from core import engine,project
from core.reference import read_sheet
from core.tramo import parse_aux,aux_bounds
from core.exporter import export_subpark


def config():
    return dict(parque='RSA-01',circuito='C01',nivel='1',tipo='AÉREO',rota='Principal',
        condutor='CA',folga=.05,reserva=0,corte_fim='PERMITIDO',sheet='PLANO DE CORTE')


def aux_row(pole,distance):
    return [None]*8+[pole,None,None,distance]


class TramoTests(unittest.TestCase):
    def test_current_row_distance_and_zero_boundaries(self):
        data=[aux_row('P1',0),aux_row('P2',10.01),aux_row('P3',20.02),
              aux_row('P3',0),aux_row('P4',30.03),aux_row('P.',0)]
        rows,bounds=parse_aux(data,config(),1,6)
        self.assertEqual(len(rows),9)
        self.assertEqual((rows[0]['de'],rows[0]['para'],rows[0]['linear']),('SE','P2',10.01))
        self.assertEqual((rows[6]['de'],rows[6]['para'],rows[6]['linear']),('SE','P4',30.03))
        self.assertEqual(bounds,3)
        # O poste L=0 é excluído e reinicia o próximo tramo na SE.
        self.assertEqual(len(engine.segments(rows)),6)
        self.assertFalse(any(r['de']=='P1' or r['para']=='P1' for r in rows))
        self.assertEqual([r['ordem'] for r in rows],[1]*3+[2]*3+[3]*3)

    def test_missing_previous_or_formula_and_negative_are_blocked(self):
        for data in [[aux_row('P1',0),aux_row('P2',None)],
                     [aux_row('P1',0),aux_row('P2',-10)], [aux_row('P1',0),aux_row('P.',10)]]:
            with self.subTest(data=data),self.assertRaises(ValueError):
                parse_aux(data,config(),1,len(data))

    def test_subpark_export_has_all_phases_and_calculated_reels_only_for_selected_park(self):
        p=project.new_project('Obra Teste')
        rows,_=parse_aux([aux_row('P1',0),aux_row('P2',10.01),aux_row('P3',20.02)],config(),1,3)
        p['trechos']=list(rows)
        p['bobinas']=[dict(id=f'B{i}',condutor='CA',tipo='AÉREO',nominal=100,real=100,utilizado=0) for i in range(3)]
        other={**rows[0],'id':'OTHER','parque':'RSA-02','fase':'A','de':'Q1','para':'Q2','linear':5}
        p['trechos'].append(other)
        p['plano']=engine.optimize(p,5)
        content=export_subpark(p,'RSA-01')
        w=openpyxl.load_workbook(io.BytesIO(content),data_only=True)
        self.assertEqual(w.sheetnames,['PLANO DE CORTE','LANÇAMENTOS','RESUMO_BOBINAS','CRITÉRIOS'])
        exported=list(w['PLANO DE CORTE'].values)[4:]
        self.assertEqual(len(exported),6)
        self.assertEqual([r[2] for r in exported],list('ABCABC'))
        assigned={ident:c['bobina'] for c in p['plano']['cortes'] for ident in c['trechos']}
        self.assertEqual(sorted(r[5] for r in exported),sorted(assigned[r['id']] for r in rows))
        self.assertEqual(exported[0][6:9],('SE','P2',10.01))
        self.assertFalse(any('Q1' in r for r in exported))
        summary=list(w['RESUMO_BOBINAS'].values)[4:]
        self.assertEqual(sum(r[4] for r in summary),sum(c['projeto'] for c in p['plano']['cortes'] if c['parque']=='RSA-01'))
        w.close()
        p['trechos'][0]['linear']+=1
        with self.assertRaises(ValueError):export_subpark(p,'RSA-01')

    def test_uploaded_aux_reference(self):
        path=Path('../upload/AUX TRAMO-RSA01-0B.xlsx')
        if not path.exists():self.skipTest('Referência privada não incluída')
        data=read_sheet(path.read_bytes(),'PLANO DE CORTE')
        self.assertEqual(aux_bounds(data),(3,4,74))
        rows,_=parse_aux(data,config(),4,74)
        self.assertEqual(len(rows),198)
        self.assertEqual((rows[0]['de'],rows[0]['para'],rows[0]['linear']),('SE','P.0/7D (AD4)',50.09))
        self.assertFalse(any(r['de']=='P.' or r['para']=='P.' for r in rows))
        self.assertAlmostEqual(rows[-1]['linear'],234.72)

    def test_aux_preview_import_and_final_download_ui(self):
        from streamlit.testing.v1 import AppTest
        from core.exporter import workbook
        # O fixture usa as mesmas colunas I/L e cabeçalho da referência real.
        headers=[None]*8+['POSTE',None,None,'DISTÂNCIA TRAMO']
        content=workbook([('PLANO DE CORTE','AUX','Referência',headers,[aux_row('P1',0),aux_row('P2',10.01)], [12]*12)])
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'RMT_DB_PATH':tmp+'/aux.sqlite3'}):
            app=AppTest.from_string('''
import streamlit as st
from core.reference_ui import render_mapping
if 'edit_version' not in st.session_state: st.session_state.edit_version=0
render_mapping(st.session_state.project,st.session_state.content,'aux.xlsx','test',st.session_state.config)
''',default_timeout=30)
            app.session_state['project']=project.new_project()
            app.session_state['content']=content
            app.session_state['config']=config()
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(next(s for s in app.selectbox if s.label=='Formato da referência').value,'AUX TRAMO: postes em I e distância em L')
            self.assertFalse(app.error)
            next(b for b in app.button if b.label=='Importar referência para este lançamento').click().run()
            self.assertFalse(app.exception)
            p=app.session_state['project']
            self.assertEqual(len(p['trechos']),3)
            p['bobinas']=[dict(id='B1',condutor='CA',tipo='AÉREO',nominal=100,real=100,utilizado=0)]
            p['plano']=engine.optimize(p,5)
            main=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
            main.session_state['project']=p
            main.sidebar.radio[0].set_value('Subparques').run()
            self.assertFalse(main.exception)
            self.assertTrue(any(b.label=='Baixar Excel final deste subparque' for b in main.get('download_button')))


if __name__=='__main__':unittest.main()
