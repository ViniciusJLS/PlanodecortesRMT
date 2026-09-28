import os
import tempfile
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest


class Interface(unittest.TestCase):
    def test_pages_and_calculation(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ['RMT_DB_PATH']=tmp+'/test.sqlite3'
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
            self.assertEqual(len(app.exception),0)
            for page in ['Projeto e importação','Traçado','Bobinas','Critérios de corte','Plano e entregáveis']:
                app.sidebar.radio[0].set_value(page).run()
                self.assertEqual(len(app.exception),0, page)
            next(b for b in app.button if b.label=='Gerar plano de corte').click().run(timeout=45)
            self.assertEqual(len(app.exception),0)
            self.assertIsNotNone(app.session_state['project']['plano'])
            self.assertGreater(len(app.session_state['project']['plano']['cortes']),0)
            app.sidebar.radio[0].set_value('Visão geral').run()
            self.assertEqual(len(app.exception),0)
            del os.environ['RMT_DB_PATH']


if __name__=='__main__':unittest.main()
