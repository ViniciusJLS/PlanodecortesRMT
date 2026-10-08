import copy
import unittest
from core import engine, project
from core.inventory import summarize, row_style


class HistoricalNominal(unittest.TestCase):
    def sample(self,previous=1467,real=None):
        p=project.demo()
        p['trechos']=p['trechos'][:1]
        p['trechos'][0].update(linear=100,folga=0,reserva=0)
        p['bobinas']=p['bobinas'][:2]
        p['bobinas'][0].update(nominal=1500,real=real,utilizado=previous)
        p['bobinas'][1].update(nominal=1500,real=None,utilizado=0)
        return p

    def test_history_exceeds_97_by_12_without_blocking_other_reels(self):
        p=self.sample()
        self.assertEqual(engine.input_errors(p),[])
        self.assertEqual(len(engine.input_warnings(p)),1)
        self.assertEqual(engine.available(p['bobinas'][0]),-12)
        result=engine.optimize(p,5)
        self.assertTrue(all(c['bobina']==p['bobinas'][1]['id'] for c in result['cortes']))
        self.assertEqual(engine.validate(p,result['cortes']),[])
        inventory=engine.stock(p,result['cortes'])
        self.assertIn('real a confirmar',inventory[0]['classificacao'])

    def test_new_allocation_never_uses_nominal_without_measurement(self):
        p=self.sample(previous=0)
        p['bobinas']=p['bobinas'][:1]
        p['trechos'][0]['linear']=1467
        with self.assertRaises(ValueError):engine.optimize(p,5)
        cut=engine.make_cut(p['trechos'],p['bobinas'][0]['id'],1)
        self.assertTrue(any('excede' in e for e in engine.validate(p,[cut])))

    def test_history_above_nominal_or_confirmed_real_remains_error(self):
        for previous,real in [(1501,None),(1467,1460)]:
            p=self.sample(previous,real)
            self.assertTrue(engine.input_errors(p))
            self.assertFalse(engine.input_warnings(p))

    def test_real_measurement_releases_only_confirmed_remaining_length(self):
        p=self.sample(1467,1500)
        self.assertEqual(engine.available(p['bobinas'][0]),33)
        self.assertEqual(engine.input_warnings(p),[])
        p['trechos'][0].update(linear=30,fixa=p['bobinas'][0]['id'])
        self.assertEqual(engine.optimize(p,5)['cortes'][0]['bobina'],p['bobinas'][0]['id'])
        p['trechos'][0]['linear']=34
        with self.assertRaises(ValueError):engine.optimize(p,5)

    def test_summary_warns_without_hiding_negative_conservative_balance(self):
        p=self.sample()
        rows,_,_=summarize(p)
        r=rows[0]
        self.assertEqual(r['Saldo disponível [m]'],-12)
        self.assertIn('real a confirmar',r['Situação'])
        self.assertIn('#92400e',row_style(r)[0])
        p['bobinas'][0]['utilizado']=1501
        r=summarize(p)[0][0]
        self.assertEqual(r['Situação'],'Excedida')
        self.assertIn('#b91c1c',row_style(r)[0])
