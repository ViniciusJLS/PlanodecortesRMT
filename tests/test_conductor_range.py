import copy
import os
import tempfile
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from core import project
from core.conductor_range import paths, interval_ids, apply_interval
from core.conductors import options


class ConductorRange(unittest.TestCase):
    def work(self):
        p=project.demo();template=copy.deepcopy(p['trechos'][0]);p['trechos']=[]
        nodes=['P.7/7A (AA38)','P.1/10A','P.1/2A','P.0/1A (AA1)']
        for phase in 'ABC':
            for i in range(3):
                row=copy.deepcopy(template)
                row.update(id=f'{phase}{i}',fase=phase,ordem=i+1,de=nodes[i],para=nodes[i+1],
                    corte_fim='PERMITIDO',linear=100,condutor='CA MAGNOLIA 954 MCM',bobina_original='DEMO-MAG-001')
                p['trechos'].append(row)
        return p

    def test_adjacent_intervals_have_no_overlap_and_cross_current_conductors(self):
        p=self.work();route=paths(p,'DEMO-01','AÉREO')[0]
        orchid=next(c for c in options(p,'AÉREO') if 'ORCHID' in c)
        oxlip=next(c for c in options(p,'AÉREO') if 'OXLIP' in c)
        q=apply_interval(p,'DEMO-01','AÉREO',route,1,2,list('ABC'),orchid)
        q=apply_interval(q,'DEMO-01','AÉREO',paths(q,'DEMO-01','AÉREO')[0],2,3,list('ABC'),oxlip)
        for phase in 'ABC':
            self.assertEqual([r['condutor'] for r in q['trechos'] if r['fase']==phase],['CA MAGNOLIA 954 MCM',orchid,oxlip])
        self.assertEqual(len(paths(q,'DEMO-01','AÉREO')),1)
        self.assertEqual(len(interval_ids(q,'DEMO-01','AÉREO',route,0,3,list('ABC'))),9)
        self.assertEqual(p['trechos'][1]['condutor'],'CA MAGNOLIA 954 MCM')
        self.assertEqual(q['trechos'][1]['bobina_original'],'')
        self.assertIsNone(q['plano'])
        self.assertFalse(q['criterios_confirmados'])

    def test_phase_and_scope_isolation(self):
        p=self.work();other=copy.deepcopy(p['trechos'][0]);other.update(id='OTHER',parque='OTHER');p['trechos'].append(other)
        route=paths(p,'DEMO-01','AÉREO')[0]
        name=next(c for c in options(p,'AÉREO') if 'OXLIP' in c)
        q=apply_interval(p,'DEMO-01','AÉREO',route,0,2,['A'],name)
        changed=[r['id'] for r in q['trechos'] if r['condutor']==name]
        self.assertEqual(changed,['A0','A1'])
        with self.assertRaises(ValueError):interval_ids(p,'OTHER','AÉREO',route,0,2,['A'])

    def test_gap_and_incomplete_phase_cannot_be_silently_included(self):
        p=self.work();p['trechos'][1]['de']='DISCONNECTED'
        self.assertGreater(len(paths(p,'DEMO-01','AÉREO')),1)
        p=self.work();route=paths(p,'DEMO-01','AÉREO')[0];p['trechos']=[r for r in p['trechos'] if r['id']!='B1']
        with self.assertRaisesRegex(ValueError,'Fase B'):interval_ids(p,'DEMO-01','AÉREO',route,0,3,list('ABC'))
        with self.assertRaises(ValueError):interval_ids(p,'DEMO-01','AÉREO',route,2,1,['A'])

    def test_forbidden_boundary_prevents_conductor_change(self):
        p=self.work()
        for r in p['trechos']:
            if r['ordem']==1:r['sem_corte_para']=True
            if r['ordem']==2:r['sem_corte_de']=True
        route=paths(p,'DEMO-01','AÉREO')[0]
        name=next(c for c in options(p,'AÉREO') if 'OXLIP' in c)
        with self.assertRaisesRegex(ValueError,'estrutura sem corte'):apply_interval(p,'DEMO-01','AÉREO',route,1,3,list('ABC'),name)

    def test_ui_apply_saves_and_updates_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            old=os.environ.get('RMT_DB_PATH');os.environ['RMT_DB_PATH']=tmp+'/test.sqlite3'
            try:
                app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
                app.session_state['project']=self.work()
                app.sidebar.radio[0].set_value('Subparques').run()
                self.assertEqual(len(app.exception),0)
                first=next(w for w in app.selectbox if w.label=='Poste inicial')
                self.assertEqual(first.options[1:],['P.7/7A (AA38)','P.1/10A','P.1/2A','P.0/1A (AA1)'])
                first.set_value('P.1/10A').run()
                next(w for w in app.selectbox if w.label=='Poste final').set_value('P.0/1A (AA1)').run()
                name=next(c for c in options(app.session_state['project'],'AÉREO') if 'OXLIP' in c)
                next(w for w in app.selectbox if w.label=='Condutor do intervalo').set_value(name).run()
                next(w for w in app.button if w.label=='Aplicar condutor').click().run()
                self.assertEqual(len(app.exception),0)
                q=app.session_state['project']
                self.assertEqual(sum(r['condutor']==name for r in q['trechos']),6)
                saved=project.load(q['id'])
                self.assertEqual(saved['trechos'],q['trechos'])
            finally:
                if old is None:os.environ.pop('RMT_DB_PATH',None)
                else:os.environ['RMT_DB_PATH']=old
