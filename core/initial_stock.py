"""Cadastro único do estoque solicitado para a obra Dom Inocêncio Sul."""
import copy
import json
from pathlib import Path
from . import project as projects
from .engine import dec
from .inventory import park_id
from .importer import norm

WORK_NAME='Dom Inocêncio Sul'
MIGRATION='estoque_dom_inocencio_sul_2026_10_07'


def source_stock():
    return json.loads(Path(__file__).with_name('bobinas_dom_inocencio_sul.json').read_text(encoding='utf-8'))


def apply_stock(work):
    """Acrescenta apenas IDs ausentes; nunca substitui edições existentes."""
    if norm(work['nome'])!=norm(WORK_NAME):
        raise ValueError('Este estoque pertence à obra Dom Inocêncio Sul.')
    candidate=copy.deepcopy(work)
    if MIGRATION in candidate.get('cadastros_aplicados',{}):return candidate,0
    source=source_stock()
    ids={r['id'] for r in candidate['bobinas']}
    scope={park_id(r['parque']) for r in candidate['trechos']}
    added=0
    for original in source['bobinas']:
        if original['id'] in ids:continue
        reel=copy.deepcopy(original)
        # Trechos já presentes são replanejados pela obra, como no importador
        # legado: a utilização desse parque não é descontada duas vezes.
        history={park_id(k):v for k,v in reel.get('consumo_importado_parques',{}).items()}
        excluded=scope & set(history)
        reel['utilizado']=float(dec(reel['utilizado'])-sum((dec(history[k]) for k in excluded),dec(0)))
        reel['parques_replanejados']=sorted(excluded)
        reel['arquivo_origem']=source['arquivo']
        candidate['bobinas'].append(reel)
        ids.add(reel['id'])
        added+=1
    candidate.setdefault('cadastros_aplicados',{})[MIGRATION]=dict(
        arquivo=source['arquivo'],sha256=source['sha256'],adicionadas=added,
        existentes=len(source['bobinas'])-added,total_referencia=len(source['bobinas']))
    if added:
        candidate['plano']=None
        candidate['criterios_confirmados']=False
    return candidate,added


def ensure_stock(active_work):
    """Cria/localiza somente a obra solicitada e persiste a migração uma vez."""
    matches=[ident for ident,name,_ in projects.saved_projects() if norm(name)==norm(WORK_NAME)]
    if norm(active_work['nome'])==norm(WORK_NAME):
        target=active_work
    elif matches:
        target=projects.load(matches[0])
    else:
        target=projects.new_project(WORK_NAME)
    if MIGRATION in target.get('cadastros_aplicados',{}):return target,0
    candidate,added=apply_stock(target)
    projects.save(candidate)
    return candidate,added
