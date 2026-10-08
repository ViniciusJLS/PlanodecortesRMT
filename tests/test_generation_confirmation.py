import os
import tempfile
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest


class GenerationConfirmation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=os.environ.get('RMT_DB_PATH')
        os.environ['RMT_DB_PATH']=self.tmp.name+'/test.sqlite3'
        self.app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        self.app.session_state['project']['criterios_confirmados']=False
        self.app.sidebar.radio[0].set_value('Plano e entregáveis').run()

    def tearDown(self):
        if self.old is None:os.environ.pop('RMT_DB_PATH',None)
        else:os.environ['RMT_DB_PATH']=self.old
        self.tmp.cleanup()

    def click(self,label):
        next(b for b in self.app.button if b.label==label).click().run(timeout=45)
        self.assertEqual(len(self.app.exception),0)

    def test_unreviewed_can_generate_after_explicit_confirmation(self):
        self.click('Gerar plano de corte')
        self.assertIsNone(self.app.session_state['project']['plano'])
        self.assertTrue(any('Deseja continuar' in m.value for m in self.app.markdown))
        self.click('Sim, continuar e gerar')
        plan=self.app.session_state['project']['plano']
        self.assertTrue(plan['cortes'])
        self.assertTrue(plan['revisao_pendente'])
        self.assertFalse(self.app.session_state['project']['criterios_confirmados'])

    def test_cancel_and_data_changes_discard_confirmation(self):
        self.click('Gerar plano de corte')
        self.click('Não, revisar pendências')
        self.assertFalse(any(b.label=='Sim, continuar e gerar' for b in self.app.button))
        self.click('Gerar plano de corte')
        self.app.session_state['project']['trechos'][0]['linear']+=1
        self.app.run()
        self.assertFalse(any(b.label=='Sim, continuar e gerar' for b in self.app.button))
        self.assertIsNone(self.app.session_state['project']['plano'])

    def test_invalid_lengths_are_shown_and_still_rejected(self):
        self.app.session_state['project']['trechos'][0]['linear']=-1
        self.app.run()
        self.click('Gerar plano de corte')
        self.assertTrue(any('linear inválido' in str(df.value) for df in self.app.dataframe))
        self.click('Sim, continuar e gerar')
        self.assertIsNone(self.app.session_state['project']['plano'])
        self.assertTrue(any('Não foi possível' in error.value for error in self.app.error))
