import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core import project
from core.reference import register_park, apply_reference, reference_template, read_sheet, guess_header, guess_mapping, parse_reference
from core.inventory import summarize


class WorkIsolation(unittest.TestCase):
    def test_same_subpark_reference_and_reel_names_are_isolated(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'RMT_DB_PATH':tmp+'/works.sqlite3'}):
            a=project.create_work('Obra Sul','SUL')
            b=project.create_work('Obra Norte','NORTE')
            for work in (a,b):
                work['bobinas']=[dict(id='B1',condutor='CA',tipo='AÉREO',nominal=1000,real=None,utilizado=0)]
                content=reference_template()
                data=read_sheet(content,'Traçado')
                header=guess_header(data)
                mapping=guess_mapping(data[header-1],'1')
                config=dict(parque='RSA-01',circuito='C01',nivel='1',tipo='AÉREO',rota='Principal',
                            condutor='CA',folga=.05,reserva=0,corte_fim='PERMITIDO',sheet='Traçado')
                rows,_=parse_reference(data,mapping,config,header+1,len(data))
                candidate=apply_reference(work,config,rows,content,work['nome']+'.xlsx',mapping,(header+1,len(data)),'expand',False)
                work.update(candidate)
                project.save(work)
            before=copy.deepcopy(project.load(b['id']))
            a['trechos'][0]['linear']=999
            a['trechos'][0]['bobina_original']='B1'
            a['bobinas'][0]['real']=50
            a['referencias_subparques']['RSA-01'].clear()
            project.save(a)
            self.assertEqual(project.load(b['id']),before)
            self.assertEqual(summarize(project.load(b['id']))[0][0]['Total utilizado [m]'],0)
            self.assertGreater(summarize(project.load(a['id']))[0][0]['Total utilizado [m]'],0)

    def test_legacy_project_and_backup_become_independent_works(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'RMT_DB_PATH':tmp+'/works.sqlite3'}):
            old=project.demo()
            old.pop('subparques',None)
            project.save(old)
            restored=project.restore(json.dumps(old))
            project.save(restored)
            self.assertNotEqual(restored['id'],old['id'])
            restored['trechos'][0]['linear']=1
            project.save(restored)
            self.assertEqual(project.load(old['id'])['trechos'][0]['linear'],240.35)
            self.assertEqual(len(project.saved_projects()),2)

    def test_sidebar_switch_discards_old_widgets_but_preserves_saved_data(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'RMT_DB_PATH':tmp+'/works.sqlite3'}):
            a=project.create_work('Sul')
            a,_=register_park(a,'RSA-01');project.save(a)
            b=project.create_work('Norte')
            b,_=register_park(b,'RSA-01');project.save(b)
            before=copy.deepcopy(project.load(b['id']))
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
            self.assertEqual(app.session_state['project']['id'],b['id'])
            picker=lambda:next(s for s in app.selectbox if s.label=='Obra ativa')
            picker().set_value(a['id']).run()
            app.sidebar.radio[0].set_value('Subparques').run()
            next(s for s in app.selectbox if s.label=='Circuito do lançamento').set_value('C34').run()
            app.session_state['project']['codigo']='SUL-EDITADA'
            picker().set_value(b['id']).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['project']['id'],b['id'])
            self.assertEqual(app.session_state['project']['codigo'],before['codigo'])
            self.assertEqual(next(s for s in app.selectbox if s.label=='Circuito do lançamento').value,'C01')
            self.assertEqual(project.load(a['id'])['codigo'],'SUL-EDITADA')
            app.sidebar.radio[0].set_value('Obras').run()
            next(t for t in app.text_input if t.label=='Nome da obra').set_value('Obra Nova')
            next(button for button in app.button if button.label=='Cadastrar e abrir obra').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['project']['nome'],'Obra Nova')
            self.assertEqual(app.session_state['project']['trechos'],[])
            self.assertEqual(app.session_state['project']['bobinas'],[])
            self.assertEqual(len(project.saved_projects()),3)


if __name__=='__main__':unittest.main()
