import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core import engine, project
from core.inventory import summarize, row_style
from core.subparks import CIRCUITS, LEVELS, phase_groups, replace_group, table_html


def sample():
    p = project.new_project('Teste de subparques')
    p['bobinas'] = [dict(id='B1', condutor='CA', tipo='AÉREO', nominal=1000, real=None,
        utilizado=200, consumo_importado_parques={'RSA01':999, 'RSA02':777, 'RSA03':200},
        parques_replanejados=['RSA01', 'RSA02']),
        dict(id='S1', condutor='XLPE', tipo='SUBTERRÂNEO', nominal=1000, real=None, utilizado=0)]
    for park, count, distance in [('RSA-01', 3, 10.01), ('RSA-02', 1, 100)]:
        for phase in 'ABC':
            for i in range(count):
                p['trechos'].append(dict(id=f'{park}-{phase}-{i}', parque=park, circuito='7',
                    nivel='1', fase=phase, tipo='AÉREO', condutor='CA', rota='B1', ordem=i+1,
                    de=f'P{i}', para=f'P{i+1}', linear=distance, folga=.05 if count==3 else 0,
                    reserva=0, corte_fim='PERMITIDO', fixa='', bobina_original='B1', observacao=''))
    return p


def edit_payload(p, index=0):
    groups, _, _ = phase_groups(p, 'RSA-01', installation='AÉREO')
    group = groups[index]
    common = {f:group[0][f] for f in ('circuito','nivel','ordem','de','para','rota','corte_fim')}
    rows = [{f:r[f] for f in ('fase','condutor','bobina_original','linear','folga','reserva','observacao')} for r in group]
    return [r['id'] for r in group], common, rows


class SubparkUpdates(unittest.TestCase):
    def test_live_summary_replaces_import_once_and_uses_real_length(self):
        p = sample()
        rows, parks, current = summarize(p)
        b = rows[0]
        self.assertFalse(current)
        self.assertEqual((b['RSA01'], b['RSA02'], b['RSA03']), (96, 300, 200))
        self.assertEqual(b['Total utilizado [m]'], 596)
        self.assertEqual(b['Saldo disponível [m]'], 374)
        p['bobinas'][0]['real'] = 500
        self.assertEqual(summarize(p)[0][0]['Saldo disponível [m]'], -96)
        self.assertIn('#b91c1c', row_style(summarize(p)[0][0])[0])

    def test_save_c34_level3_preserves_other_park_and_database(self):
        p = sample()
        ids, common, rows = edit_payload(p)
        common.update(circuito='C34', nivel='3')
        q = replace_group(p, 'RSA-01', 'AÉREO', ids, common, rows)
        self.assertEqual([r['nivel'] for r in q['trechos'] if r['id'] in ids], ['3']*3)
        self.assertEqual([r['circuito'] for r in q['trechos'] if r['id'] in ids], ['C34']*3)
        self.assertEqual(len(q['trechos']), len(p['trechos']))
        self.assertEqual([r['linear'] for r in q['trechos'] if r['parque']=='RSA-02'], [100]*3)
        self.assertEqual(summarize(q)[0][0]['RSA02'], 300)
        self.assertEqual(p['trechos'][0]['circuito'], '7')
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'RMT_DB_PATH':tmp+'/test.sqlite3'}):
            project.save(q)
            restored = project.load(q['id'])
            self.assertEqual(restored, q)
            self.assertEqual(summarize(restored), summarize(q))

    def test_underground_three_phases_and_reserves_not_multiplied_twice(self):
        p = sample()
        common = dict(circuito='C34', nivel='3', ordem=1, de='CX1', para='T1', rota='Sub', corte_fim='PERMITIDO')
        rows = [dict(fase=phase, condutor='XLPE', bobina_original='S1', linear=40.8, folga=.02,
            qte_caixas=2, sobra_caixa=18, qte_postes=2, sobra_poste=20,
            qte_turbinas=0, sobra_turbina=0, reserva_outros=0, observacao='') for phase in 'ABC']
        q = replace_group(p, 'RSA-01', 'SUBTERRÂNEO', [], common, rows)
        groups, warnings, _ = phase_groups(q, 'RSA-01', 'C34', '3', 'SUBTERRÂNEO')
        self.assertFalse(warnings)
        self.assertEqual([r['fase'] for r in groups[0]], list('ABC'))
        self.assertEqual([r['reserva'] for r in groups[0]], [38]*3)
        self.assertEqual(summarize(q)[0][1]['RSA01'], 240)
        html = table_html(groups, underground=True)
        self.assertIn('Sobra saída turbina [m]', html)
        self.assertEqual(html.count('<tr class="group-end">'), 1)
        self.assertIn('4px double', html)

    def test_invalid_edit_is_atomic_and_circuit_normalization_keeps_continuity(self):
        p = sample()
        original = copy.deepcopy(p)
        ids, common, rows = edit_payload(p)
        common['circuito'] = 'C35'
        with self.assertRaises(ValueError): replace_group(p, 'RSA-01', 'AÉREO', ids, common, rows)
        self.assertEqual(p, original)
        common['circuito'] = 'C07'
        q = replace_group(p, 'RSA-01', 'AÉREO', ids, common, rows)
        self.assertEqual(summarize(q)[0][0]['RSA01'], 96)
        self.assertEqual(len(engine.segments(q['trechos'])), 6)
        rows[0]['bobina_original'] = 'S1'
        with self.assertRaises(ValueError): replace_group(p, 'RSA-01', 'AÉREO', ids, common, rows)
        self.assertEqual(p, original)

    def test_plan_precedence_and_other_assignments_survive_edit(self):
        p = sample()
        p['bobinas'].append(dict(id='B2', condutor='CA', tipo='AÉREO', nominal=1000, real=None, utilizado=0))
        cuts = [engine.make_cut(chain, 'B2', i) for i,chain in enumerate(engine.segments(p['trechos']))]
        p['plano'] = dict(fingerprint=engine.fingerprint(p), cortes=cuts)
        self.assertEqual(summarize(p)[0][0]['Total utilizado [m]'], 200)
        self.assertEqual(summarize(p)[0][2]['Total utilizado [m]'], 396)
        ids, common, rows = edit_payload(p)
        for r in rows:r['bobina_original'] = 'B2'
        q = replace_group(p, 'RSA-01', 'AÉREO', ids, common, rows)
        self.assertIsNone(q['plano'])
        self.assertTrue(all(r['bobina_original']=='B2' for r in q['trechos']))
        self.assertEqual(summarize(q)[0][2]['Total utilizado [m]'], 396)

    def test_invalid_length_is_pending_and_missing_assignment_does_not_bridge(self):
        p = sample()
        p['trechos'][1]['bobina_original'] = ''
        self.assertEqual(summarize(p)[0][0]['RSA01'], 86)  # 11+11 (A) + 32 (B) + 32 (C)
        p['trechos'][0]['linear'] = -1
        self.assertIsNone(summarize(p)[0][0]['Total utilizado [m]'])


class SubparkInterface(unittest.TestCase):
    def test_edit_save_switch_park_and_open_summary(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'RMT_DB_PATH':tmp+'/test.sqlite3'}):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'), default_timeout=30).run()
            app.session_state['project'] = sample()
            app.sidebar.radio[0].set_value('Subparques').run()
            self.assertFalse(app.exception)
            self.assertNotIn('Registros de fases', [m.label for m in app.metric])
            self.assertEqual([s.value for s in app.subheader], ['Rede aérea', 'Rede subterrânea'])
            select = lambda label: next(s for s in app.selectbox if s.label == label)
            self.assertEqual(select('Filtrar circuito').options, ['Todos']+CIRCUITS)
            self.assertEqual(select('Filtrar nível').options, ['Todos']+LEVELS)
            select('Trecho para editar').set_value(0).run()
            select('Circuito do trecho').set_value('C34')
            select('Nível do trecho').set_value('3')
            next(b for b in app.button if b.label == 'Salvar trecho e atualizar resumo').click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            p = app.session_state['project']
            self.assertEqual(len([r for r in p['trechos'] if r['nivel']=='3']), 3)
            select('Subparque').set_value('RSA-02').run()
            self.assertFalse(app.exception)
            select('Subparque').set_value('RSA-01').run()
            self.assertEqual(project.load(p['id'])['trechos'], app.session_state['project']['trechos'])
            next(b for b in app.button if b.label == 'Abrir Resumo de bobinas').click().run()
            self.assertEqual(app.sidebar.radio[0].value, 'Resumo de bobinas')
            self.assertFalse(app.exception)


if __name__ == '__main__':
    unittest.main()
