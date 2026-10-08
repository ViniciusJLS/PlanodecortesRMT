import copy
import unittest
from decimal import Decimal
from core import engine, project, operations


def fixture(distances,capacity=1455,reels=2,parks=None):
    p=project.demo()
    template=copy.deepcopy(p['trechos'][0])
    p['trechos']=[]
    for i,d in enumerate(distances):
        row=copy.deepcopy(template)
        row.update(id=f'T{i}',ordem=i+1,de=f'P{i}',para=f'P{i+1}',linear=d,
            folga=0,reserva=0,corte_fim='PERMITIDO',fixa='',bobina_original='',parque=parks[i] if parks else 'RSA01')
        p['trechos'].append(row)
    p['bobinas']=p['bobinas'][:reels]
    for r in p['bobinas']:r.update(nominal=capacity,real=capacity,utilizado=0)
    return p


class Operations(unittest.TestCase):
    def test_full_reel_continuous(self):
        p=fixture([800,655]);result=engine.optimize(p,10)
        self.assertEqual([c['projeto'] for c in result['cortes']],[1455])
        self.assertEqual(operations.report(p,result['cortes'])['bobinas_lancamento_completo'],1)

    def test_cut_earlier_leaves_reusable_remainders(self):
        p=fixture([900,425,475]);result=engine.optimize(p,10)
        self.assertEqual(sorted(c['projeto'] for c in result['cortes']),[900,900])
        r=operations.report(p,result['cortes'])
        self.assertEqual([v['saldo'] for v in r['bobinas']],[555,555])
        self.assertEqual(r['sobras_intermediarias'],0)
        self.assertEqual(engine.validate(p,result['cortes']),[])

    def test_physical_cut_prohibition_beats_preferences(self):
        p=fixture([900,425,475]);p['trechos'][0]['corte_fim']='PROIBIDO'
        cuts=engine.optimize(p,10)['cortes']
        self.assertEqual(sorted(c['projeto'] for c in cuts),[475,1325])
        self.assertEqual(operations.report(p,cuts)['sobras_intermediarias'],1)

    def test_boundaries(self):
        p=operations.settings({})
        expected={Decimal('60'):'Sobra tolerada',Decimal('60.01'):'Sobra intermediária a evitar',
            Decimal('500'):'Sobra intermediária a evitar',Decimal('500.01'):'Sobra reutilizável'}
        for v,label in expected.items():self.assertEqual(operations.remainder_class(v,p),label)

    def test_proximity_beats_park_number(self):
        parks=['RSA09','RSA01','RSA02'];p=fixture([600]*3,1300,2,parks)
        p['criterios']['proximidades']=[dict(parque_a=a,parque_b=b,proximidade=v) for a,b,v in
            [('RSA09','RSA02','Próximos'),('RSA09','RSA01','Distantes'),('RSA01','RSA02','Distantes')]]
        cuts=engine.optimize(p,10)['cortes']
        transfers=operations.report(p,cuts)['transportes']
        self.assertEqual(len(transfers),1)
        self.assertEqual({transfers[0]['de'],transfers[0]['para']},{'RSA09','RSA02'})

    def test_execution_order_counts_only_successive_parks(self):
        p=fixture([600]*3,2000,1,['RSA09','RSA01','RSA02'])
        p['criterios']['ordem_execucao']=['RSA09','RSA02','RSA01']
        result=engine.optimize(p,10)
        r=operations.report(p,result['cortes'])
        self.assertEqual([(t['de'],t['para']) for t in r['transportes']],[('RSA09','RSA02'),('RSA02','RSA01')])
        self.assertEqual(r['indice_transporte'],6)
        stage=next(s for s in result['etapas'] if s['criterio']=='Índice de transporte entre parques')
        self.assertEqual(stage['valor'],6)

    def test_defaults_are_isolated_and_version_invalidates_plan(self):
        a,b=project.new_project(),project.new_project()
        a['criterios']['proximidades'].append({'test':1})
        self.assertEqual(b['criterios']['proximidades'],[])
        p=fixture([800]);before=engine.fingerprint(p)
        p['criterios']['sobra_tolerada']=50
        self.assertNotEqual(before,engine.fingerprint(p))

    def test_invalid_limits_stop_optimization(self):
        p=fixture([800]);p['criterios']['sobra_reutilizavel']=60
        with self.assertRaisesRegex(ValueError,'Limites operacionais'):engine.optimize(p,5)

    def test_quick_mode_does_not_claim_priority_optimum(self):
        p=fixture([900,425,475]);result=engine.optimize(p,10,'rapido')
        self.assertIn('não comprovadamente',result['status'])
        self.assertEqual(engine.validate(p,result['cortes']),[])

    def test_scoped_optimization_accounts_for_preserved_park_proximity(self):
        from core.reference import optimize_scope
        p=fixture([600]*3,1300,2,['RSA09','RSA01','RSA02'])
        p['trechos'][0]['bobina_original']=p['bobinas'][0]['id']
        p['trechos'][1]['bobina_original']=p['bobinas'][1]['id']
        p['criterios']['proximidades']=[dict(parque_a='RSA02',parque_b=b,proximidade=v)
            for b,v in [('RSA09','Próximos'),('RSA01','Distantes')]]
        result=optimize_scope(p,'RSA02',10)
        chosen=next(c for c in result['cortes'] if c['parque']=='RSA02')
        self.assertEqual(chosen['bobina'],p['bobinas'][0]['id'])
        self.assertEqual(engine.validate(p,result['cortes']),[])

    def test_criteria_ui_saves_per_work_and_invalidates_plan(self):
        import os
        import tempfile
        from pathlib import Path
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as tmp:
            old=os.environ.get('RMT_DB_PATH')
            os.environ['RMT_DB_PATH']=tmp+'/test.sqlite3'
            try:
                app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
                app.sidebar.radio[0].set_value('Critérios de corte').run()
                next(n for n in app.number_input if n.label=='Sobra tolerada até [m]').set_value(70.)
                next(b for b in app.button if b.label=='Salvar critérios').click().run()
                self.assertEqual(len(app.exception),0)
                self.assertEqual(app.session_state['project']['criterios']['sobra_tolerada'],70)
                self.assertIsNone(app.session_state['project']['plano'])
            finally:
                if old is None:os.environ.pop('RMT_DB_PATH',None)
                else:os.environ['RMT_DB_PATH']=old
