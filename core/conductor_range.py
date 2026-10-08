"""Seleção de vãos contínuos por postes, independente do condutor atual."""
from collections import defaultdict
from .conductors import assign
from .subparks import circuit_id


def scope(row):
    return (circuit_id(row['circuito']), str(row['nivel']), row.get('rota',''), row.get('bloco_tramo',''))


def paths(project, park, installation, circuit=None, level=None):
    grouped=defaultdict(list)
    for row in project['trechos']:
        if row['parque']!=park or row['tipo']!=installation:continue
        if circuit and circuit_id(row['circuito'])!=circuit:continue
        if level and str(row['nivel'])!=str(level):continue
        grouped[(scope(row),row['fase'])].append(row)
    result=[]
    seen=set()
    for (route,phase),rows in sorted(grouped.items(),key=lambda v:str(v[0])):
        rows=sorted(rows,key=lambda r:r['ordem'])
        if len({r['ordem'] for r in rows})!=len(rows):
            raise ValueError('Há ordens repetidas na rota. Corrija a tabela antes de selecionar um intervalo.')
        chains=[]
        for row in rows:
            if not chains or chains[-1][-1]['para']!=row['de']:chains.append([])
            chains[-1].append(row)
        for chain in chains:
            signature=(route,tuple((r['ordem'],r['de'],r['para']) for r in chain))
            if signature in seen:continue
            seen.add(signature)
            result.append(dict(scope=route,ids=[r['id'] for r in chain],
                nodes=[chain[0]['de']]+[r['para'] for r in chain],phase=phase))
    return result


def interval_ids(project, park, installation, path, start, end, phases):
    if not phases or not set(phases)<={'A','B','C'}:
        raise ValueError('Selecione ao menos uma fase A, B ou C.')
    if not (isinstance(start,int) and isinstance(end,int) and 0<=start<end<len(path['nodes'])):
        raise ValueError('O poste final deve estar depois do inicial no sentido da rota.')
    indexed={r['id']:r for r in project['trechos']}
    try:anchor=[indexed[i] for i in path['ids']]
    except KeyError:raise ValueError('Os trechos mudaram. Selecione novamente a rota.')
    if any(r['parque']!=park or r['tipo']!=installation or scope(r)!=path['scope'] for r in anchor):
        raise ValueError('A rota não pertence ao subparque e instalação selecionados.')
    if [anchor[0]['de']]+[r['para'] for r in anchor]!=path['nodes'] or any(a['para']!=b['de'] for a,b in zip(anchor,anchor[1:])):
        raise ValueError('A rota mudou ou apresenta descontinuidade. Selecione novamente.')
    selected=anchor[start:end]
    expected=[(r['ordem'],r['de'],r['para']) for r in selected]
    ids=[]
    for phase in phases:
        rows=[r for r in project['trechos'] if r['parque']==park and r['tipo']==installation and
            scope(r)==path['scope'] and r['fase']==phase and selected[0]['ordem']<=r['ordem']<=selected[-1]['ordem']]
        rows.sort(key=lambda r:r['ordem'])
        if [(r['ordem'],r['de'],r['para']) for r in rows]!=expected:
            raise ValueError(f'Fase {phase}: intervalo incompleto ou diferente. Confira os vãos antes de aplicar.')
        ids.extend(r['id'] for r in rows)
    return ids


def apply_interval(project,park,installation,path,start,end,phases,description):
    ids=interval_ids(project,park,installation,path,start,end,phases)
    return assign(project,park,ids,description,installation)
