import copy
import unittest
from core import engine, project


class ContinuousBlocks(unittest.TestCase):
    def work(self):
        p=project.demo();template=copy.deepcopy(p['trechos'][0]);p['trechos']=[]
        for phase in 'ABC':
            for i,(start,end) in enumerate([('SE','GAVETA'),('GAVETA','AMARRACAO'),('AMARRACAO','FINAL')]):
                row=copy.deepcopy(template)
                row.update(id=f'{phase}{i}',fase=phase,de=start,para=end,ordem=i+1,linear=400,
                    folga=0,reserva=0,bloco_tramo='1' if i==0 else '2',bobina_original='',fixa='',
                    corte_fim='PROIBIDO' if i==0 else 'PERMITIDO',sem_corte_de=i==1,sem_corte_para=i==0)
                p['trechos'].append(row)
        return p

    def test_empty_reels_are_allocated_from_se_across_reference_blocks(self):
        p=self.work()
        self.assertEqual(engine.input_errors(p),[])
        cuts=engine.optimize(p,10)['cortes']
        self.assertEqual(len(cuts),3)
        self.assertTrue(all(c['de']=='SE' and c['para']=='FINAL' and c['projeto']==1200 for c in cuts))
        self.assertEqual(engine.validate(p,cuts),[])

    def test_boundary_still_cannot_cut_even_if_metadata_is_changed(self):
        p=self.work()
        for r in p['trechos']:r['corte_fim']='PERMITIDO'
        invalid=[engine.make_cut([r],p['bobinas'][0]['id'],i+1) for i,r in enumerate(p['trechos'])]
        self.assertTrue(any('sem corte' in e or 'proibido' in e for e in engine.validate(p,invalid)))
        self.assertTrue(all(c['de']!='GAVETA' and c['para']!='GAVETA' for c in engine.optimize(p,10)['cortes']))

    def test_missing_span_is_not_fabricated(self):
        p=self.work()
        for r in p['trechos']:
            if r['ordem']==2:r['de']='OUTRO POSTE'
        self.assertTrue(any('corte proibido' in e for e in engine.input_errors(p)))

    def test_different_conductor_or_route_prevents_continuous_launch(self):
        for field,value in [('condutor','CA OXLIP 4/0 AWG'),('rota','OUTRA ROTA')]:
            p=self.work()
            for r in p['trechos']:
                if r['ordem']>1:r[field]=value
            self.assertTrue(engine.input_errors(p))

    def test_branch_is_not_chosen_arbitrarily(self):
        p=self.work();p['trechos']=[r for r in p['trechos'] if r['fase']=='A']
        branch=copy.deepcopy(p['trechos'][1]);branch.update(id='RAMAL',bloco_tramo='3',para='RAMAL FIM',ordem=4)
        p['trechos'].append(branch)
        chains=engine.segments(p['trechos'])
        self.assertTrue(any(len(c)==1 and c[0]['de']=='SE' for c in chains))
