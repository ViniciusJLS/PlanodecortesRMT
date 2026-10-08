"""Corrige origens importadas da regra antiga sem sobrescrever edições manuais."""
import base64
import copy
import hashlib
from .reference import read_sheet, scope_key
from .importer import number, text
from .tramo import restricted_rows


def migrate(project):
    refs=project.get('referencias_subparques',{})
    pending=[(park,ref) for park,values in refs.items() for ref in values.values()
             if ref.get('phase_mode')=='aux_tramo' and ref.get('config',{}).get('aux_zero_version',0)<2]
    if not pending:return project,0
    candidate=copy.deepcopy(project)
    count=0
    for park,ref in [(park,ref) for park,values in candidate['referencias_subparques'].items() for ref in values.values()
                     if ref.get('phase_mode')=='aux_tramo' and ref.get('config',{}).get('aux_zero_version',0)<2]:
        encoded=candidate.get('arquivos_referencia',{}).get(ref.get('sha256'))
        if not encoded:continue
        content=base64.b64decode(encoded)
        if hashlib.sha256(content).hexdigest()!=ref['sha256']:
            raise ValueError('A referência salva não corresponde à identificação do arquivo.')
        data=read_sheet(content,ref['sheet'])
        restrictions=restricted_rows(content,ref['sheet'])
        config=ref['config']
        origin=text(config.get('origem_inicial')) or 'SE'
        target=scope_key(config)
        for row in candidate['trechos']:
            if scope_key(row)!=target:continue
            source=row.get('referencia_de_linha',0)
            destination=row.get('referencia_para_linha',0)
            if not (0<source<=len(data) and 0<destination<=len(data)):continue
            previous,current=data[source-1],data[destination-1]
            if len(previous)<12 or len(current)<12:continue
            if number(previous[11])!=0 or not number(current[11]) or number(current[11])<0:continue
            # Only repair the exact former origin from the saved workbook.
            if row['de']!=text(previous[8]) or row['para']!=text(current[8]):continue
            row['de']=origin
            row['sem_corte_de']=False
            row['referencia_de_linha']=0
            row['origem']=f"{ref['sheet']}!origem {origin} → I{destination} / L{destination}; I{source} com L=0 excluída"
            old_note='Sem corte na estrutura: '+row.get('restricao_estrutura','')
            row['restricao_estrutura']=str(restrictions.get(destination,''))
            if not row.get('observacao') or row['observacao']==old_note:
                row['observacao']='Sem corte na estrutura: '+row['restricao_estrutura'] if row['restricao_estrutura'] else ''
            count+=1
        config['aux_zero_version']=2
        config['origem_inicial']=origin
        config['distancia_inicial']=0
    if count:
        candidate['plano']=None
        candidate['criterios_confirmados']=False
    return candidate,count
