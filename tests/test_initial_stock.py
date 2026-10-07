import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core import project
from core.initial_stock import apply_stock,ensure_stock,source_stock,WORK_NAME,MIGRATION


class InitialStockTests(unittest.TestCase):
    def test_source_matches_uploaded_inventory_and_nominal_rule(self):
        rows=source_stock()['bobinas']
        self.assertEqual(len(rows),384)
        self.assertEqual(len({r['id'] for r in rows}),384)
        self.assertEqual(sum(r['tipo']=='AÉREO' for r in rows),369)
        self.assertEqual(sum(r['tipo']=='SUBTERRÂNEO' for r in rows),15)
        self.assertTrue(all(r['real'] is None for r in rows))
        path=Path('../upload/PLANO DE CORTE RMT - DOM INOCÊNCIO SUL 3(3).xlsx')
        if path.exists():
            from core.importer import import_control
            self.assertEqual(rows,import_control(path.read_bytes(),[])[1])

    def test_register_is_idempotent_preserves_user_edits_and_other_rows(self):
        p=project.new_project(WORK_NAME)
        source=source_stock()['bobinas'][0]
        existing={**source,'real':1950,'utilizado':10}
        p['bobinas']=[existing,dict(id='MANUAL',condutor='CA',tipo='AÉREO',nominal=100,real=100,utilizado=0)]
        p['plano']={'status':'antigo'}
        before=copy.deepcopy(p)
        q,count=apply_stock(p)
        self.assertEqual(count,383)
        self.assertEqual(q['bobinas'][0],existing)
        self.assertEqual(q['bobinas'][1]['id'],'MANUAL')
        self.assertEqual(len(q['bobinas']),385)
        self.assertIsNone(q['plano'])
        self.assertEqual(p,before)
        q['bobinas'][0]['real']=1960
        q['bobinas'].pop()
        again,count=apply_stock(q)
        self.assertEqual(count,0)
        self.assertEqual(again,q) # edição/exclusão depois da migração não é desfeita

    def test_existing_park_history_is_excluded_once(self):
        p=project.new_project(WORK_NAME)
        p['trechos']=[dict(parque='RSA-01')]
        q,_=apply_stock(p)
        reel=q['bobinas'][0]
        self.assertEqual(reel['utilizado'],0)
        self.assertEqual(reel['parques_replanejados'],['RSA01'])
        self.assertEqual(reel['consumo_importado_parques']['RSA01'],1845)
        again,_=apply_stock(q)
        self.assertEqual(again['bobinas'][0],reel)

    def test_persistence_is_scoped_to_named_work_and_preserves_active_other_work(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'RMT_DB_PATH':tmp+'/db'}):
            other=project.create_work('Outra obra')
            target,count=ensure_stock(other)
            self.assertEqual((target['nome'],count),(WORK_NAME,384))
            self.assertEqual(project.load(other['id'])['bobinas'],[])
            self.assertEqual(len(project.load(target['id'])['bobinas']),384)
            again,count=ensure_stock(other)
            self.assertEqual(count,0)
            self.assertEqual(again['id'],target['id'])
            with self.assertRaises(ValueError):apply_stock(other)

    def test_app_stock_page_has_persisted_inventory(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'RMT_DB_PATH':tmp+'/db'}):
            work=project.create_work(WORK_NAME)
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
            self.assertFalse(app.exception)
            app.sidebar.radio[0].set_value('Bobinas').run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.session_state['project']['bobinas']),384)
            self.assertEqual(len(project.load(work['id'])['bobinas']),384)
            self.assertTrue(any('384 bobinas adicionadas' in x.value for x in app.info))
            self.assertIn(MIGRATION,project.load(work['id'])['cadastros_aplicados'])


if __name__=='__main__':unittest.main()
