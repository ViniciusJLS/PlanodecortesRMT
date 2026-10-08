import copy
import unittest
from core import project, engine
from core.overview import chart_data, pie


class Overview(unittest.TestCase):
    def sample(self):
        p=project.new_project('Teste')
        p['subparques']=['RSA01','RSA02','RSA03']
        p['bobinas']=[dict(id='B1',condutor='MAG',nominal=1500,real=1455,utilizado=700,
            consumo_importado_parques={'RSA01':400,'RSA02':300}),
            dict(id='B2',condutor='MAG',nominal=1500,real=None,utilizado=100,
            consumo_importado_parques={'RSA02':100}),
            dict(id='B3',condutor='OUTRO',nominal=1000,real=None,utilizado=200,
            consumo_importado_parques={'RSA01':200})]
        return p

    def test_shared_reel_counted_once_and_lengths_added(self):
        data=chart_data(self.sample())
        self.assertEqual(data['conductors'],[
            {'Condutor':'MAG','Bobinas utilizadas':2,'Comprimento [m]':800.},
            {'Condutor':'OUTRO','Bobinas utilizadas':1,'Comprimento [m]':200.}])
        self.assertIn('RSA03',data['parks'])
        self.assertEqual(sum(r['Comprimento [m]'] for r in data['details']),1000)

    def test_current_plan_replaces_imported_active_park_and_stale_plan_ignored(self):
        p=self.sample()
        row=copy.deepcopy(project.demo()['trechos'][0]);row.update(parque='RSA01',bobina_original='B1',linear=250,folga=0,reserva=0)
        p['trechos']=[row]
        p['plano']={'fingerprint':engine.fingerprint(p),'cortes':[dict(bobina='B1',parque='RSA01',projeto=350)]}
        data=chart_data(p)
        self.assertTrue(data['current'])
        self.assertEqual(sum(r['Comprimento [m]'] for r in data['details']),750)
        p['plano']['fingerprint']='old'
        data=chart_data(p)
        self.assertFalse(data['current'])
        self.assertEqual(sum(r['Comprimento [m]'] for r in data['details']),650)

    def test_empty_duplicate_and_unassigned(self):
        self.assertEqual(chart_data(project.new_project())['details'],[])
        p=self.sample();p['bobinas'][0]['utilizado']+=50
        self.assertEqual(chart_data(p)['unassigned'],50)
        p['bobinas'].append(copy.deepcopy(p['bobinas'][0]))
        data=chart_data(p)
        self.assertEqual(data['pending'],2)
        self.assertFalse(any(r['Bobina']=='B1' for r in data['details']))

    def test_pie_schema_and_readable_tooltips(self):
        import pandas as pd
        spec=pie(pd.DataFrame(chart_data(self.sample())['conductors']),'Condutor','Comprimento [m]').to_dict()
        self.assertEqual(spec['mark']['type'],'arc')
        self.assertEqual(spec['encoding']['theta']['field'],'value')
        self.assertEqual(spec['encoding']['theta']['title'],'Comprimento [m]')
        self.assertEqual(spec['transform'][0]['joinaggregate'][0]['field'],'value')
        values = next(iter(spec['datasets'].values()))
        self.assertEqual(sum(v['value'] for v in values),1000)
        self.assertTrue(all(set(v)=={'category','value'} for v in values))
        self.assertEqual(len(spec['encoding']['tooltip']),3)
