import copy
import json
import unittest
from pathlib import Path
from core import engine
from core.tramo import parse_aux
from core.aux_zero_migration import migrate
from test_tramo import config, aux_row


class ZeroOrigins(unittest.TestCase):
    def test_zero_poles_are_removed_and_se_span_uses_next_positive_distance(self):
        data=[aux_row('INEXISTENTE',0),aux_row('REAL1',54.7),aux_row('REAL2',79.45)]
        rows,_=parse_aux(data,config(),1,3,{1:'Esforço 1000 em gaveta',2:'Esforço 1000 em gaveta'})
        self.assertEqual([(r['de'],r['para'],r['linear']) for r in rows[::3]],[('SE','REAL1',54.7),('REAL1','REAL2',79.45)])
        self.assertTrue(all(not r['sem_corte_de'] for r in rows[:3]))
        self.assertTrue(all(r['sem_corte_para'] for r in rows[:3]))
        self.assertFalse(any('INEXISTENTE' in (r['de'],r['para']) for r in rows))

    def test_zero_does_not_create_span_even_with_legacy_initial_distance(self):
        rows,_=parse_aux([aux_row('FAKE',0),aux_row('REAL',25)],{**config(),'origem_inicial':'SE','distancia_inicial':99},1,2)
        self.assertEqual(len(rows),3)
        self.assertTrue(all(r['linear']==25 and r['de']=='SE' and r['para']=='REAL' for r in rows))

    def test_real_backup_correction_preserves_values_and_removes_errors(self):
        path=Path('../upload/obra_rmt_924417f6.json')
        if not path.exists():self.skipTest('Backup privado não incluído')
        p=json.loads(path.read_text());before=copy.deepcopy(p)
        q,count=migrate(p)
        self.assertEqual(count,12)
        self.assertEqual(p,before)
        self.assertEqual(q['bobinas'],p['bobinas'])
        self.assertEqual(len(q['trechos']),198)
        self.assertEqual(engine.input_errors(q),[])
        fake={'P.0/8D (AD5)','P.0/9C (AC7)','P.7/7A (AA38)','P.0/3B (AB3)'}
        self.assertFalse(any(r['de'] in fake or r['para'] in fake for r in q['trechos']))
        for a,b in zip(p['trechos'],q['trechos']):
            for field in ('id','condutor','linear','folga','reserva','bobina_original','fixa'):
                self.assertEqual(a[field],b[field])
        self.assertIs(migrate(q)[0],q)
        self.assertEqual(migrate(q)[1],0)
