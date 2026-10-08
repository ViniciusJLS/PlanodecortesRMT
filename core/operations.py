"""Preferências operacionais: continuidade, sobras e transporte entre parques."""
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_FLOOR
from itertools import combinations
import math

VERSION=1
PROXIMITY={'Próximos':1,'Intermediários':2,'Não informada':3,'Distantes':4}
DEFAULTS=dict(versao_operacional=VERSION,sobra_tolerada=60,sobra_reutilizavel=500,
    lancamento_minimo=500,proximidades=[],ordem_execucao=[])


def settings(project):
    return {**DEFAULTS,**project.get('criterios',{})}


def parameter_errors(project):
    p=settings(project)
    errors=[]
    try:
        values=[float(p[k]) for k in ('sobra_tolerada','sobra_reutilizavel','lancamento_minimo')]
        if any(not math.isfinite(v) or v<0 or v>1000000 for v in values) or values[1]<=values[0]:
            raise ValueError()
    except (ValueError,TypeError):errors.append('Limites operacionais inválidos: use valores de 0 a 1.000.000 m e sobra reutilizável maior que a tolerada.')
    seen=set()
    for row in p['proximidades']:
        a,b=row.get('parque_a'),row.get('parque_b')
        pair=tuple(sorted((str(a or ''),str(b or ''))))
        if not a or not b or a==b or pair in seen or row.get('proximidade') not in PROXIMITY:
            errors.append('Proximidades: informe pares distintos, sem repetição, e uma classificação válida.')
        seen.add(pair)
    order=p['ordem_execucao']
    if any(not isinstance(x,str) or not x.strip() for x in order) or len(set(order))!=len(order):
        errors.append('Ordem de execução contém parques vazios ou repetidos.')
    return errors


def pair_score(params,a,b):
    for row in params['proximidades']:
        if {row['parque_a'],row['parque_b']}=={a,b}:
            return PROXIMITY[row['proximidade']]
    return PROXIMITY['Não informada']


def ordered_parks(params,parks):
    order=params['ordem_execucao']
    return [p for p in order if p in parks] if set(parks)<=set(order) else None


def remainder_class(value,params):
    if value<0:return 'Saldo excedido'
    if value==0:return 'Esgotada'
    if value<=Decimal(str(params['sobra_tolerada'])):return 'Sobra tolerada'
    if value<=Decimal(str(params['sobra_reutilizavel'])):return 'Sobra intermediária a evitar'
    return 'Sobra reutilizável'


def objectives(model,candidates,by_reel,reels,available,project):
    """Retorna objetivos em ordem estrita; restrições físicas são mantidas."""
    p=settings(project)
    cents=lambda x:int((Decimal(str(x))*100).to_integral_value(rounding=ROUND_FLOOR))
    low,high=cents(p['sobra_tolerada']),cents(p['sobra_reutilizavel'])
    fixed=project.get('_cortes_preservados_operacao',[])
    fixed_counts=Counter(c['bobina'] for c in fixed)
    fixed_parks=defaultdict(set)
    for c in fixed:fixed_parks[c['bobina']].add(c['parque'])
    all_parks={r['parque'] for r in project['trechos']} | {c['parque'] for c in fixed}
    order=ordered_parks(p,all_parks)
    full,bad,transport,committed=[],[],[],[]
    per_park=defaultdict(lambda:defaultdict(list))
    for x,rows,j,size in candidates:per_park[j][rows[0]['parque']].append(x)
    for j,terms in by_reel.items():
        cap=cents(available(reels[j]))
        count=sum(x for x,_ in terms)
        used=sum(x*size*100 for x,size in terms)
        opened=model.new_bool_var(f'opened_{j}')
        model.add(count>=opened)
        model.add(count<=len(terms)*opened)
        model.add(used<=cap)
        committed.append(cap*opened)
        active=1 if fixed_counts[reels[j]['id']] else opened
        rem=model.new_int_var(0,cap,f'remainder_{j}')
        model.add(rem==cap*active-used)
        above=model.new_bool_var(f'above_{j}')
        model.add(rem>low).only_enforce_if(above)
        model.add(rem<=low).only_enforce_if(above.Not())
        below=model.new_bool_var(f'below_{j}')
        model.add(rem<=high).only_enforce_if(below)
        model.add(rem>high).only_enforce_if(below.Not())
        intermediate=model.new_bool_var(f'intermediate_{j}')
        model.add(intermediate<=above);model.add(intermediate<=below)
        model.add(intermediate>=above+below-1)
        bad.append(intermediate)
        if not fixed_counts[reels[j]['id']]:
            single=model.new_bool_var(f'single_{j}')
            model.add(count==1).only_enforce_if(single)
            model.add(count!=1).only_enforce_if(single.Not())
            complete=model.new_bool_var(f'complete_{j}')
            model.add(complete<=single);model.add(complete+above<=1)
            model.add(complete>=single-above)
            full.append(complete)
        parks={}
        for park in set(per_park[j]) | fixed_parks[reels[j]['id']]:
            if park in fixed_parks[reels[j]['id']]:parks[park]=1
            else:
                present=model.new_bool_var(f'park_{j}_{len(parks)}')
                model.add_max_equality(present,per_park[j][park])
                parks[park]=present
        sequence=[a for a in order if a in parks] if order is not None else sorted(parks)
        for ai,a in enumerate(sequence):
            for bi in range(ai+1,len(sequence)):
                b=sequence[bi]
                between=[parks[k] for k in sequence[ai+1:bi]] if order is not None else []
                shared=model.new_bool_var(f'transfer_{j}_{ai}_{bi}')
                model.add(shared<=parks[a]);model.add(shared<=parks[b])
                for middle in between:model.add(shared+middle<=1)
                model.add(shared>=parks[a]+parks[b]-1-sum(between))
                transport.append(pair_score(p,a,b)*shared)
    short=sum(x for x,rows,j,size in candidates if size<=float(p['lancamento_minimo']))
    return [('Lançamentos contínuos',sum(x for x,*_ in candidates)),
        ('Bobinas em um lançamento com sobra tolerada',-sum(full)),
        ('Sobras intermediárias e lançamentos curtos',sum(bad)+short),
        ('Índice de transporte entre parques',sum(transport)),
        ('Metragem de estoque mobilizada',sum(committed))]


def report(project,cuts):
    from .engine import available
    p=settings(project)
    grouped=defaultdict(list)
    for c in cuts:grouped[c['bobina']].append(c)
    reels={r['id']:r for r in project['bobinas']}
    all_parks={c['parque'] for c in cuts}
    order=ordered_parks(p,all_parks)
    inventory=[]
    transfers=[]
    for ident,launches in grouped.items():
        if ident not in reels:continue
        remaining=available(reels[ident])-sum((Decimal(str(c['projeto'])) for c in launches),Decimal(0))
        inventory.append(dict(bobina=ident,lancamentos=len(launches),saldo=float(remaining),
            classificacao=remainder_class(remaining,p),
            lancamento_completo=len(launches)==1 and 0<=remaining<=Decimal(str(p['sobra_tolerada']))))
        parks={c['parque'] for c in launches}
        sequence=[a for a in order if a in parks] if order is not None else sorted(parks)
        pairs=zip(sequence,sequence[1:]) if order is not None else combinations(sequence,2)
        for a,b in pairs:
            score=pair_score(p,a,b)
            transfers.append(dict(bobina=ident,de=a,para=b,proximidade=next(k for k,v in PROXIMITY.items() if v==score),indice=score))
    short=[dict(lancamento=c['id'],bobina=c['bobina'],parque=c['parque'],comprimento=c['projeto']) for c in cuts if c['projeto']<=float(p['lancamento_minimo'])]
    return dict(lancamentos=len(cuts),bobinas_lancamento_completo=sum(r['lancamento_completo'] for r in inventory),
        sobras_intermediarias=sum(r['classificacao']=='Sobra intermediária a evitar' for r in inventory),
        lancamentos_curtos=short,bobinas=inventory,transportes=transfers,indice_transporte=sum(r['indice'] for r in transfers),
        transporte_por_ordem=order is not None)


def criteria_rows(project,cuts):
    p=settings(project);r=report(project,cuts)
    from .engine import input_warnings
    return [['Prioridades','Menos lançamentos; bobinas em lançamento único com sobra tolerada; evitar sobras intermediárias e operações curtas; proximidade; estoque mobilizado'],
        ['Sobra tolerada até [m]',p['sobra_tolerada']],['Sobra reutilizável acima de [m]',p['sobra_reutilizavel']],
        ['Lançamento curto até [m]',p['lancamento_minimo']],
        ['Ordem de execução',' → '.join(p['ordem_execucao']) or 'Não definida; transporte avaliado por pares de parques'],
        ['Lançamentos curtos no plano',len(r['lancamentos_curtos'])],['Sobras intermediárias no plano',r['sobras_intermediarias']],
        ['Índice de transporte',r['indice_transporte']],['Custos','Indicadores operacionais relativos; não estimam valores em reais nem horas de equipe'],
        *[['Metragem histórica a confirmar',v] for v in input_warnings(project)],
        *[[f"Proximidade: {v['parque_a']} / {v['parque_b']}",v['proximidade']] for v in p['proximidades']]]
