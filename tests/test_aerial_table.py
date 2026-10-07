import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core.aerial_table import rows_and_columns, aerial_table_html, balances
from core.subparks import phase_groups
from core import engine, project


def sample():
    p=project.new_project()
    p['bobinas']=[dict(id=f'B{level}',condutor=f'CA{level}',tipo='AÉREO',nominal=200,real=200,utilizado=20) for level in (1,2)]
    for order in (1,2):
        for level in (1,2):
            for phase in 'ABC':
                p['trechos'].append(dict(id=f'{order}-{level}-{phase}',parque='RSA-01',circuito=f'C0{level}',nivel=str(level),
                    fase=phase,tipo='AÉREO',condutor=f'CA{level}',rota='Principal',ordem=order,de=f'P{order}',para=f'P{order+1}',
                    linear=10.01,folga=.05,reserva=0,corte_fim='PERMITIDO',fixa='',bobina_original=f'B{level}',observacao=''))
    return p


class AerialTableTests(unittest.TestCase):
    def test_reference_columns_and_two_levels_share_abc_without_mutation(self):
        p=sample()
        for r in p['trechos']:
            if r['nivel']=='2':r['ordem']=float(r['ordem'])
        before=copy.deepcopy(p)
        groups,_,_=phase_groups(p,'RSA-01',installation='AÉREO')
        columns,rows=rows_and_columns(p,groups)
        self.assertEqual([title for _,title in columns],[
            'DESCRIÇÃO (NIVEL 1)','BOBINA (NIVEL 1)','CIRCUITO (NIVEL 1)',
            'DESCRIÇÃO (NIVEL 2)','BOBINA (NIVEL 2)','CIRCUITO (NIVEL 2)',
            'FASE','TIPO','DE','PARA','DISTÂNCIA PROJETO','SOBRA BOBINA 1','SOBRA BOBINA 2','OBSERVAÇÕES'])
        self.assertEqual(len(rows),2)
        self.assertEqual([r['fase'] for g in rows for r in g],list('ABCABC'))
        self.assertEqual((rows[0][0]['bobina_1'],rows[0][0]['bobina_2']),('B1','B2'))
        self.assertEqual(rows[0][0]['distancia_projeto'],'10,51')
        self.assertEqual(rows[0][0]['sobra_1'],'114,00')
        html=aerial_table_html(p,groups)
        self.assertEqual(html.count('<tr class="group-end">'),2)
        self.assertNotIn('<th>DISTÂNCIA LINEAR</th>',html)
        self.assertNotIn('<th>FOLGA DESNÍVEL</th>',html)
        self.assertEqual(p,before)

    def test_filters_third_level_conflicting_lengths_and_duplicate_circuits_are_retained(self):
        p=sample()
        extra=[{**r,'id':'extra-'+r['id'],'nivel':'3','circuito':'C03','condutor':'CA3','bobina_original':'','reserva':5} for r in p['trechos'] if r['nivel']=='1' and r['ordem']==1]
        p['trechos']+=extra
        groups,_,_=phase_groups(p,'RSA-01',installation='AÉREO')
        columns,rows=rows_and_columns(p,groups)
        self.assertIn(('sobra_3','SOBRA BOBINA 3'),columns)
        self.assertIn('N3: 15,51',rows[0][0]['distancia_projeto'])
        groups,_,_=phase_groups(p,'RSA-01','C02','2','AÉREO')
        _,rows=rows_and_columns(p,groups)
        self.assertEqual(len(rows),2)
        self.assertNotIn('descricao_1',rows[0][0])
        self.assertEqual(rows[0][0]['circuito_2'],'C02')
        # Dois circuitos no mesmo nível e vão são preservados em grupos separados.
        p['trechos']+=[{**r,'id':'duplicate-'+r['id'],'circuito':'C04'} for r in list(p['trechos']) if r['nivel']=='1' and r['ordem']==1]
        groups,_,_=phase_groups(p,'RSA-01',installation='AÉREO')
        _,rows=rows_and_columns(p,groups)
        self.assertEqual(len(rows),3)
        self.assertEqual({g[0].get('circuito_1') for g in rows},{'C01','C04'})

    def test_current_plan_reels_and_global_balance_include_other_subpark(self):
        p=sample()
        p['trechos'].append({**p['trechos'][0],'id':'other','parque':'RSA-02','linear':5,'folga':0})
        p['plano']=engine.optimize(p,5)
        groups,_,_=phase_groups(p,'RSA-01',installation='AÉREO')
        _,rows=rows_and_columns(p,groups)
        used=sum(c['projeto'] for c in p['plano']['cortes'] if c['bobina']=='B1')
        self.assertEqual(balances(p)['B1'],180-used)
        self.assertEqual(rows[0][0]['sobra_1'],f'{180-used},00')

    def test_subpark_ui_renders_reference_headers(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'RMT_DB_PATH':tmp+'/db'}):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
            app.session_state['project']=sample()
            app.sidebar.radio[0].set_value('Subparques').run()
            self.assertFalse(app.exception)
            table=next(m.value for m in app.markdown if '<table aria-label=' in m.value)
            self.assertIn('<th>DESCRIÇÃO (NIVEL 1)</th>',table)
            self.assertIn('<th>BOBINA (NIVEL 2)</th>',table)
            self.assertNotIn('<th>Linear [m]</th>',table)


if __name__=='__main__':unittest.main()
