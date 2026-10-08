import copy
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED
from core import engine, project
from core.conductors import catalog, parse_catalog, assign, register
from core.tramo import parse_aux, restricted_rows
from core.exporter import workbook, export_subpark
from test_tramo import config, aux_row


class ConductorAndRestrictionTests(unittest.TestCase):
    def work(self):
        p=project.new_project()
        p['trechos'],_=parse_aux([aux_row('P1',0),aux_row('P2',10),aux_row('P3',20)],config(),1,3,{2:'Azul'})
        p['bobinas']=[dict(id='B1',condutor='CA',tipo='AÉREO',real=100,nominal=100,utilizado=0)]
        return p

    def test_zero_context_initial_se_and_current_distance(self):
        cfg={**config(),'origem_inicial':'SE','distancia_inicial':40,'linha_inicial':3}
        rows,_=parse_aux([aux_row('P1',0),aux_row('P2',88.49),aux_row('P87',0),aux_row('P88',25)],cfg,1,4)
        self.assertEqual([(r['de'],r['para'],r['linear']) for r in rows[::3]],
            [('SE','P2',88.49),('SE','P88',25)])
        self.assertTrue(all(r['linear']>0 for r in rows))
        cfg={**config(),'origem_inicial':'SE'}
        rows,_=parse_aux([aux_row('P87',55)],cfg,1,1)
        self.assertEqual((rows[0]['de'],rows[0]['para'],rows[0]['linear']),('SE','P87',55))

    def test_color_styles_and_gaveta_read_from_ooxml(self):
        headers=[None]*8+['POSTE','ALTURA/ESFORÇO','POSIÇÃO','DISTÂNCIA TRAMO']
        data=[aux_row('P1',0),aux_row('P2',10),aux_row('P3',20),aux_row('P4',30)]
        data[3][9:11]=['12/1000','GAVETA']
        original=workbook([('PLANO DE CORTE','AUX','',headers,data,[12]*12)])
        # Fixture OOXML: fonte azul RGB, preenchimento azul indexado e esforço sem cor.
        target=io.BytesIO()
        with ZipFile(io.BytesIO(original)) as source,ZipFile(target,'w',ZIP_DEFLATED) as out:
            import re
            count=int(re.search(r'<cellXfs count="(\d+)">',source.read('xl/styles.xml').decode()).group(1))
            for name in source.namelist():
                xml=source.read(name)
                if name=='xl/styles.xml':
                    value=xml.decode().replace('<fonts count="4">','<fonts count="5">')
                    value=value.replace('</fonts>','<font><color rgb="FF0000FF"/></font></fonts>')
                    value=value.replace('<fills count="3">','<fills count="4">').replace('</fills>','<fill><patternFill patternType="solid"><fgColor indexed="12"/></patternFill></fill></fills>')
                    # append new cell formats using existing style count
                    import re
                    match=re.search(r'<cellXfs count="(\d+)">',value)
                    count=int(match.group(1))
                    value=value.replace(match.group(0),f'<cellXfs count="{count+2}">').replace('</cellXfs>','<xf numFmtId="0" fontId="4" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0"/></cellXfs>')
                    xml=value.encode()
                if name=='xl/worksheets/sheet1.xml':
                    value=xml.decode()
                    import re
                    value=re.sub(r'<c r="I6"[^>]*>',f'<c r="I6" s="{count}" t="inlineStr">',value)
                    value=re.sub(r'<c r="I7"[^>]*>',f'<c r="I7" s="{count+1}" t="inlineStr">',value)
                    xml=value.encode()
                out.writestr(name,xml)
        restrictions=restricted_rows(target.getvalue(),'PLANO DE CORTE')
        self.assertEqual(restrictions,{6:'Marcação azul',7:'Marcação azul',8:'Esforço 1000 em gaveta'})

    def test_no_cut_at_blue_node_even_after_manual_override(self):
        p=self.work()
        for r in p['trechos']:r['corte_fim']='PERMITIDO'
        plan=engine.optimize(p,5)
        self.assertTrue(all(c['de']=='SE' and c['para']=='P3' for c in plan['cortes']))
        self.assertFalse(engine.validate(p,plan['cortes']))
        bad=[engine.make_cut([r], 'B1',i) for i,r in enumerate(p['trechos'])]
        self.assertTrue(any('proibido' in e or 'sem corte' in e for e in engine.validate(p,bad)))
        p['trechos']=[r for r in p['trechos'] if r['ordem']==2]
        self.assertTrue(any('começa' in e for e in engine.input_errors(p)))

    def test_final_excel_contains_restrictions_and_allocations(self):
        import openpyxl
        p=self.work()
        p['plano']=engine.optimize(p,5)
        w=openpyxl.load_workbook(io.BytesIO(export_subpark(p,'RSA-01')),data_only=True)
        records=list(w['PLANO DE CORTE'].values)
        self.assertEqual(records[3][-2:],('Corte no fim','Estrutura sem corte'))
        self.assertEqual(records[4][-2:],('PROIBIDO','Azul'))
        self.assertEqual(records[4][5],'B1')
        self.assertEqual(records[4][8],10)
        w.close()

    def test_catalog_and_atomic_selection_preserve_other_work_and_stock(self):
        p=self.work()
        self.assertEqual(len(catalog(p)),62)
        other=copy.deepcopy(p)
        p['plano']=engine.optimize(p,5)
        desc='CA MAGNOLIA 954 MCM'
        before=copy.deepcopy(p)
        with self.assertRaises(ValueError):assign(p,'RSA-01',[r['id'] for r in p['trechos'] if r['ordem']==1],desc,'AÉREO')
        self.assertEqual(p,before)
        unrelated={**p['trechos'][0],'id':'OTHER','parque':'RSA-02','sem_corte_para':False,'corte_fim':'PERMITIDO'}
        p['trechos'].append(unrelated)
        selected=assign(p,'RSA-01',[r['id'] for r in p['trechos'] if r['parque']=='RSA-01'],desc,'AÉREO')
        self.assertEqual(next(r for r in selected['trechos'] if r['id']=='OTHER'),unrelated)
        self.assertTrue(all(r['condutor']==desc and not r['bobina_original'] for r in selected['trechos'] if r['parque']=='RSA-01'))
        self.assertEqual(selected['bobinas'],p['bobinas'])
        self.assertEqual(other['trechos'][0]['condutor'],'CA')
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'RMT_DB_PATH':tmp+'/db'}):
            candidate=register(selected,[dict(descricao='NOVO',tipo='AÉREO',dados={})])
            project.save(candidate)
            self.assertTrue(any(r['descricao']=='NOVO' for r in catalog(project.load(candidate['id']))))

    def test_uploaded_catalog(self):
        path=Path('../upload/Dados Condutores(1).xlsx')
        if not path.exists():self.skipTest('Referência privada não incluída')
        self.assertEqual(sorted(parse_catalog(path.read_bytes(),path.name),key=lambda r:(r['tipo'],r['descricao'])),catalog(project.new_project()))

    def test_catalog_page_and_batch_selection_ui(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'RMT_DB_PATH':tmp+'/db'}):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
            p=self.work()
            app.session_state['project']=p
            app.sidebar.radio[0].set_value('Condutores').run()
            self.assertFalse(app.exception)
            app.sidebar.radio[0].set_value('Subparques').run()
            self.assertFalse(app.exception)
            next(w for w in app.multiselect if w.label=='Trechos que receberão o condutor').set_value([0,1])
            choice=next(s for s in app.selectbox if s.label=='Condutor para os trechos selecionados')
            choice.set_value('CA MAGNOLIA 954 MCM')
            next(b for b in app.button if b.label=='Aplicar condutor aos trechos').click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            self.assertTrue(all(r['condutor']=='CA MAGNOLIA 954 MCM' for r in app.session_state['project']['trechos']))


if __name__=='__main__':unittest.main()
