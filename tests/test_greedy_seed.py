import copy
import unittest
from core import project, engine
from core.greedy_seed import prepare


class GreedySeed(unittest.TestCase):
    def work(self):
        p=project.demo();p['trechos']=p['trechos'][:1]
        p['trechos'][0].update(linear=100,folga=0,reserva=0)
        source=p['bobinas'][1]
        p['bobinas']=[{**source,'id':f'B{i}'} for i in range(100)]
        return p

    def test_equivalent_reels_reduced_to_feasible_launch_bound(self):
        p=self.work();before=copy.deepcopy(p)
        reels,cuts=prepare(p,engine)
        self.assertEqual(len(cuts),1)
        self.assertEqual(len(reels),1)
        self.assertEqual(engine.validate(p,cuts),[])
        self.assertEqual(p,before)
        result=engine.optimize(p,5)
        self.assertEqual(engine.validate(p,result['cortes']),[])

    def test_fixed_and_preserved_reels_are_not_pruned(self):
        p=self.work();p['trechos'][0]['fixa']='B99'
        p['_cortes_preservados_operacao']=[{'bobina':'B98'}]
        reels,cuts=prepare(p,engine)
        self.assertTrue({'B98','B99'} <= {r['id'] for r in reels})
        self.assertEqual(cuts[0]['bobina'],'B99')
