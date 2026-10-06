import base64
import copy
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import openpyxl
from core import engine, project
from core.reference import (parse_reference, apply_reference, register_park, reference_template,
    read_sheet, sheets, guess_header, guess_mapping, optimize_scope)
from core.inventory import summarize


def config(park='RSA-01'):
    return dict(parque=park,circuito='C01',nivel='1',tipo='AÉREO',rota='Principal',
        condutor='CA',folga=.05,reserva=0,corte_fim='PERMITIDO',sheet='Traçado')


def parsed(cfg=None):
    content = reference_template()
    data = read_sheet(content,'Traçado')
    header = guess_header(data)
    mapping = guess_mapping(data[header-1], '1')
    rows, _ = parse_reference(data,mapping,cfg or config(),header+1,len(data))
    return rows,content,mapping,(header+1,len(data))


def sample():
    p = project.new_project('Referências')
    p['bobinas'] = [dict(id=f'B{i}',condutor='CA',tipo='AÉREO',nominal=2000,real=2000,utilizado=0) for i in range(1,4)]
    return p


class ReferenceTests(unittest.TestCase):
    def test_model_header_mapping_and_abc_generation(self):
        rows,content,_,_=parsed()
        self.assertEqual(sheets(content),['Traçado'])
        self.assertEqual(len(rows),6)
        self.assertEqual([r['fase'] for r in rows],list('ABCABC'))
        self.assertEqual([r['ordem'] for r in rows],[1,1,1,2,2,2])
        self.assertEqual(rows[0]['linear'],100.25)
        self.assertTrue(all(not r['bobina_original'] for r in rows))

    def test_phase_columns_filters_and_unrounded_reserves(self):
        rows=[['P1','P2','10,01',phase,'C34','3','SUBTERRÂNEO',2,18,20] for phase in 'ABC']
        rows.append(['Q1','Q2',20,'A','C01','1','AÉREO',5,0,0])
        mapping=dict(de=0,para=1,linear=2,fase=3,circuito=4,nivel=5,tipo=6,folga=7,sobra_caixa=8,sobra_poste=9)
        cfg=dict(config(),circuito='C34',nivel='3',tipo='SUBTERRÂNEO')
        parsed_rows,skipped=parse_reference(rows,mapping,cfg,1,4,'column',True)
        self.assertEqual(skipped,1)
        self.assertEqual([r['reserva'] for r in parsed_rows],[38]*3)
        self.assertEqual(parsed_rows[0]['folga'],.02)
        self.assertEqual(parsed_rows[0]['linear'],10.01)
        with self.assertRaisesRegex(ValueError,'precisa das fases'):
            parse_reference(rows[:2],mapping,cfg,1,2,'column',True)

    def test_invalid_reference_is_rejected_before_application(self):
        for distance in [None, '=B1', -1, float('nan')]:
            with self.subTest(distance=distance), self.assertRaises(ValueError):
                parse_reference([['P1','P2',distance]],dict(de=0,para=1,linear=2),config(),1,1)
        with self.assertRaisesRegex(ValueError,'já contém fases'):
            parse_reference([['P1','P2',10,'A']],dict(de=0,para=1,linear=2,fase=3),config(),1,1)
        with self.assertRaisesRegex(ValueError,'mais de um campo'):
            parse_reference([['P1','P2',10]],dict(de=0,para=1,linear=1),config(),1,1)

    def test_import_is_idempotent_and_preserves_parks_levels_and_file(self):
        p=sample()
        rows,content,mapping,interval=parsed()
        q=apply_reference(p,config(),rows,content,'parque.xlsx',mapping,interval,'expand',False)
        cfg2=dict(config('RSA-02'),nivel='3')
        rows2,_,_,_=parsed(cfg2)
        q=apply_reference(q,cfg2,rows2,content,'parque2.xlsx',mapping,interval,'expand',False)
        before=copy.deepcopy(q)
        replacement=copy.deepcopy(rows)
        replacement[0]['linear']=110
        q=apply_reference(q,config(),replacement,content,'parque.xlsx',mapping,interval,'expand',False)
        self.assertEqual(len(q['trechos']),12)
        self.assertEqual([r for r in q['trechos'] if r['parque']=='RSA-02'],[r for r in before['trechos'] if r['parque']=='RSA-02'])
        self.assertEqual(p['trechos'],[])
        self.assertEqual(len(q['arquivos_referencia']),1)
        self.assertEqual(base64.b64decode(next(iter(q['arquivos_referencia'].values()))),content)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'RMT_DB_PATH':tmp+'/ref.sqlite3'}):
            project.save(q)
            self.assertEqual(project.load(q['id']),q)

    def test_import_transfers_park_history_without_double_count(self):
        p=sample()
        p['bobinas'][0].update(utilizado=500,consumo_importado_parques={'RSA01':200,'RSA02':300},parques_replanejados=[])
        rows,content,mapping,interval=parsed()
        q=apply_reference(p,config(),rows,content,'a.xlsx',mapping,interval,'expand',False)
        self.assertEqual(q['bobinas'][0]['utilizado'],300)
        again=apply_reference(q,config(),rows,content,'a.xlsx',mapping,interval,'expand',False)
        self.assertEqual(again['bobinas'][0]['utilizado'],300)
        self.assertEqual(summarize(again)[0][0]['Total utilizado [m]'],300)
        p['bobinas'][0]['utilizado']=100
        with self.assertRaisesRegex(ValueError,'histórico incompatível'):
            apply_reference(p,config(),rows,content,'a.xlsx',mapping,interval,'expand',False)
        self.assertFalse(p['trechos'])

    def test_optimize_global_and_single_park_preserve_shared_stock(self):
        p=sample()
        p['trechos']=parsed()[0]+parsed(config('RSA-02'))[0]
        with self.assertRaisesRegex(ValueError,'outros parques sem bobina'):
            optimize_scope(p,'RSA-01',5)
        p['plano']=optimize_scope(p,None,5)
        self.assertEqual(engine.validate(p,p['plano']['cortes']),[])
        others=[{k:v for k,v in c.items() if k!='id'} for c in p['plano']['cortes'] if c['parque']=='RSA-02']
        plan=optimize_scope(p,'RSA-01',5)
        self.assertEqual(engine.validate(p,plan['cortes']),[])
        self.assertEqual(others,[{k:v for k,v in c.items() if k!='id'} for c in plan['cortes'] if c['parque']=='RSA-02'])
        for reel in engine.stock(p,plan['cortes']):
            self.assertGreaterEqual(reel['saldo'],0)

    def test_register_empty_park_and_alias(self):
        p=sample()
        p,name=register_park(p,'RSA-01')
        q,name=register_park(p,'RSA01')
        self.assertEqual(name,'RSA-01')
        self.assertEqual(q['subparques'],['RSA-01'])


class ReferenceUI(unittest.TestCase):
    def test_empty_park_registration_and_model_import_preview(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'RMT_DB_PATH':tmp+'/ui.sqlite3'}):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
            app.session_state['project']=sample()
            app.sidebar.radio[0].set_value('Subparques').run()
            next(x for x in app.text_input if x.label=='Nome do novo subparque').set_value('RSA-01')
            next(b for b in app.button if b.label=='Cadastrar e selecionar').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(next(s for s in app.selectbox if s.label=='Subparque').value,'RSA-01')
            self.assertTrue(any(f.label=='Excel de referência — RSA-01' for f in app.get('file_uploader')))
            # Exercita o mesmo fluxo de prévia e importação usado pelo uploader, com bytes reais de XLSX.
            harness=AppTest.from_string('''
import streamlit as st
from core.reference_ui import render_mapping
from core.reference import reference_template
if 'edit_version' not in st.session_state: st.session_state.edit_version=0
render_mapping(st.session_state.project, reference_template(), 'teste.xlsx', 'test', st.session_state.config)
''',default_timeout=30)
            harness.session_state['project']=sample()
            harness.session_state['config']=config()
            harness.run()
            self.assertFalse(harness.exception)
            self.assertFalse(harness.error)
            next(b for b in harness.button if b.label=='Importar referência para este lançamento').click().run()
            self.assertFalse(harness.exception)
            self.assertEqual(len(harness.session_state['project']['trechos']),6)
            saved=harness.session_state['project']
            self.assertEqual(project.load(saved['id'])['referencias_subparques'],saved['referencias_subparques'])
            app.session_state['project']=saved
            app.run()
            next(c for c in app.checkbox if c.label.startswith('Conferi os pontos de corte')).check().run()
            next(b for b in app.button if b.label=='Calcular bobinas e pontos de corte').click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            self.assertTrue(app.session_state['project']['plano'])
            self.assertTrue(any(b.label=='Baixar entregável Excel do plano' for b in app.get('download_button')))


if __name__=='__main__': unittest.main()
