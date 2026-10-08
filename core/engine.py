"""Regras de planejamento. Sem dependência da interface Streamlit."""
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import hashlib
import json
import math
import time
from . import operations


def dec(value):
    return Decimal(str(value))


def fingerprint(project):
    data = {k: project.get(k) for k in ('trechos', 'bobinas', 'criterios')}
    data['versao_operacional'] = operations.VERSION
    data['politica_consumo_historico'] = 1
    data['continuidade_blocos'] = 1
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def base(reel):
    real = reel.get('real')
    return dec(real) if real is not None else dec(reel['nominal']) * Decimal('0.97')


def available(reel):
    return base(reel) - dec(reel.get('utilizado', 0))


def historical_nominal_exception(reel):
    """Somente histórico sem real confirmada, entre 97% e nominal."""
    try:
        previous, nominal = dec(reel.get('utilizado', 0)), dec(reel['nominal'])
        return (reel.get('real') is None and previous.is_finite() and nominal.is_finite()
                and nominal >= 0 and base(reel) < previous <= nominal)
    except (ValueError, TypeError, KeyError, ArithmeticError):
        return False


def input_warnings(project):
    return [f"Bobina {r['id']}: consumo histórico supera a base de 97% em {dec(r.get('utilizado', 0))-base(r)} m, mas está dentro do nominal de {r['nominal']} m. Metragem real a confirmar; indisponível para novos lançamentos."
            for r in project['bobinas'] if historical_nominal_exception(r)]


def key(t):
    return tuple(str(t.get(k, '')) for k in ('parque', 'circuito', 'nivel', 'fase', 'condutor', 'tipo', 'rota', 'bloco_tramo'))


def physical_key(row):
    # Reference blocks are not physical termination points.
    return key(row)[:-1]


def raw_length(rows):
    # A folga pode variar entre trechos; arredondamento acontece UMA vez por corte.
    return sum((dec(r['linear']) * (1 + dec(r['folga'])) + dec(r.get('reserva', 0)) for r in rows), Decimal(0))


def length(rows):
    return int(raw_length(rows).to_integral_value(rounding=ROUND_CEILING))


def segments(rows):
    groups = defaultdict(list)
    for t in rows:
        groups[key(t)].append(t)
    result = []
    for k, group in sorted(groups.items()):
        chain = []
        for t in sorted(group, key=lambda r: r['ordem']):
            if chain and chain[-1]['para'] != t['de']:
                result.append(chain)
                chain = []
            chain.append(t)
        if chain:
            result.append(chain)
    # Join only unambiguous physical continuations between reference blocks.
    # Keep disconnected paths and branches separate; never invent a span.
    following, preceding = defaultdict(list), defaultdict(list)
    for i, first in enumerate(result):
        for j, second in enumerate(result):
            if i == j or physical_key(first[0]) != physical_key(second[0]):
                continue
            if (first[-1]['para'] == second[0]['de'] and
                    first[-1]['ordem'] < second[0]['ordem']):
                following[i].append(j)
                preceding[j].append(i)
    links = {i: choices[0] for i, choices in following.items()
             if len(choices) == 1 and len(preceding[choices[0]]) == 1}
    incoming = set(links.values())
    joined, visited = [], set()
    for first in [i for i in range(len(result)) if i not in incoming]:
        chain, current = [], first
        while current not in visited:
            visited.add(current)
            chain.extend(result[current])
            if current not in links:
                break
            current = links[current]
        joined.append(chain)
    joined.extend(chain for i, chain in enumerate(result) if i not in visited)
    return joined


def node_key(row, pole):
    return tuple(str(row.get(k,'')) for k in ('parque','circuito','nivel','tipo','rota'))+(pole,)


def blocked_nodes(rows):
    return {node_key(r,r[side]) for r in rows for side,flag in [('de','sem_corte_de'),('para','sem_corte_para')] if r.get(flag)}


def start_allowed(row, blocked):
    return node_key(row,row['de']) not in blocked


def end_allowed(row, blocked):
    return row['corte_fim']!='PROIBIDO' and node_key(row,row['para']) not in blocked


def input_errors(project):
    errors = operations.parameter_errors(project)
    rows, reels = project['trechos'], project['bobinas']
    for label, items in [('trecho', rows), ('bobina', reels)]:
        ids = [str(t.get('id', '')) for t in items]
        duplicates = [ident for ident, count in Counter(ids).items() if count > 1]
        if any(v in ('', 'None') for v in ids) or duplicates:
            errors.append(f'Identificações vazias ou repetidas em {label}: ' + ', '.join(duplicates[:20]))
    for r in reels:
        try:
            if not str(r.get('condutor', '')).strip():
                raise ValueError('condutor ausente')
            numbers = [dec(r['nominal']), dec(r.get('utilizado', 0))]
            if r.get('real') is not None:
                numbers.append(dec(r['real']))
            if any(not n.is_finite() or n < 0 for n in numbers):
                raise ValueError('metragem inválida')
            if available(r) < 0 and not historical_nominal_exception(r):
                raise ValueError('consumo anterior maior que a metragem real confirmada ou que o nominal permitido para histórico')
        except (ValueError, KeyError, ArithmeticError) as exc:
            errors.append(f"Bobina {r.get('id')}: {exc}.")
    orders = set()
    for t in rows:
        try:
            for field in ('parque', 'circuito', 'fase', 'condutor', 'de', 'para'):
                if t.get(field) is None or not str(t.get(field, '')).strip():
                    raise ValueError(f'{field} ausente')
            if t['de'] == t['para']:
                raise ValueError('início igual ao fim')
            for field in ('linear', 'folga', 'reserva', 'ordem'):
                v = dec(t.get(field, 0))
                if not v.is_finite() or v < 0:
                    raise ValueError(f'{field} inválido')
            if dec(t['linear']) <= 0:
                raise ValueError('distância linear deve ser positiva')
            if dec(t['folga']) > 1:
                raise ValueError('folga deve estar em fração: 0,05 representa 5%')
            if t.get('corte_fim') not in ('PERMITIDO', 'PROIBIDO', 'OBRIGATORIO'):
                raise ValueError('critério de corte inválido')
            order = (key(t), t['ordem'])
            if order in orders:
                raise ValueError('ordem repetida na mesma rota/fase/nível')
            orders.add(order)
        except (ValueError, KeyError, ArithmeticError) as exc:
            errors.append(f"Trecho {t.get('id')}: {exc}.")
    if not rows:
        errors.append('Cadastre ao menos um trecho.')
    if not reels:
        errors.append('Cadastre ao menos uma bobina.')
    if not errors:
        blocked=blocked_nodes(rows)
        for chain in segments(rows):
            if not start_allowed(chain[0],blocked):
                errors.append(f"{chain[0]['id']}: a rota/condutor começa em estrutura sem corte. Inclua o vão anterior ou mantenha o condutor contínuo.")
            if not end_allowed(chain[-1],blocked):
                errors.append(f"{chain[-1]['id']}: a rota termina em um ponto com corte proibido.")
    return errors


def make_cut(rows, reel_id, number):
    return dict(id=f'C{number:04d}', bobina=reel_id, parque=rows[0]['parque'],
                circuito=rows[0]['circuito'], nivel=rows[0]['nivel'], fase=rows[0]['fase'],
                condutor=rows[0]['condutor'], tipo=rows[0]['tipo'], de=rows[0]['de'],
                para=rows[-1]['para'], linear=float(sum((dec(r['linear']) for r in rows), Decimal(0))),
                acrescimo=float(raw_length(rows) - sum((dec(r['linear']) for r in rows), Decimal(0))),
                projeto=length(rows), trechos=[r['id'] for r in rows])


def validate(project, cuts):
    """Auditoria independente de cobertura, continuidade, critérios e balanço."""
    errors = input_errors(project)
    rows = {r['id']: r for r in project['trechos']}
    reels = {r['id']: r for r in project['bobinas']}
    coverage, consumption = Counter(), Counter()
    blocked=blocked_nodes(project['trechos'])
    for c in cuts:
        ids = c.get('trechos', [])
        coverage.update(ids)
        if not ids or any(i not in rows for i in ids) or c['bobina'] not in reels:
            errors.append(f"{c['id']}: referência inválida.")
            continue
        rs = [rows[i] for i in ids]
        reel = reels[c['bobina']]
        if any(physical_key(r) != physical_key(rs[0]) for r in rs):
            errors.append(f"{c['id']}: mistura de rotas, circuitos, fases ou condutores.")
        for a, b in zip(rs, rs[1:]):
            if a['para'] != b['de'] or a['ordem'] >= b['ordem'] or a['corte_fim'] == 'OBRIGATORIO':
                errors.append(f"{c['id']}: continuidade ou corte obrigatório violado.")
        if not start_allowed(rs[0],blocked):
            errors.append(f"{c['id']}: início em estrutura sem corte.")
        if not end_allowed(rs[-1],blocked):
            errors.append(f"{c['id']}: término em corte proibido.")
        if any(r.get('fixa') and r['fixa'] != reel['id'] for r in rs):
            errors.append(f"{c['id']}: bobina fixada não respeitada.")
        if reel['condutor'] != rs[0]['condutor'] or reel.get('tipo') != rs[0]['tipo']:
            errors.append(f"{c['id']}: bobina incompatível com o cabo.")
        if c['projeto'] != length(rs) or abs(c['linear'] - sum(float(r['linear']) for r in rs)) > 1e-6:
            errors.append(f"{c['id']}: metragem incorreta.")
        if c['de'] != rs[0]['de'] or c['para'] != rs[-1]['para']:
            errors.append(f"{c['id']}: limites incorretos.")
        consumption[c['bobina']] += c['projeto']
    if len({c['id'] for c in cuts}) != len(cuts):
        errors.append('Identificação de corte duplicada.')
    for ident in rows:
        if coverage[ident] != 1:
            errors.append(f'{ident}: cobertura {coverage[ident]} (esperado: 1).')
    for ident, used in consumption.items():
        if dec(used) > available(reels[ident]):
            errors.append(f'{ident}: consumo planejado excede o saldo em {dec(used) - available(reels[ident])} m.')
    return list(dict.fromkeys(errors))


def optimize(project, timeout=30, mode='global'):
    """Candidatos de cortes contínuos + alocação global CP-SAT.

    Atendimento integral é obrigatório. Objetivo ponderado configurável:
    número de cortes, bobinas abertas e sobras abaixo do limite reutilizável.
    Não declara impossibilidade quando apenas o limite de tempo foi atingido.
    """
    from ortools.sat.python import cp_model
    errors = input_errors(project)
    if errors:
        raise ValueError('\n'.join(errors[:50]))
    start_time = time.monotonic()
    from .greedy_seed import prepare
    import sys
    reels,seed = prepare(project,sys.modules[__name__])
    model = cp_model.CpModel()
    candidates, coverage, by_reel = [], defaultdict(list), defaultdict(list)
    blocked=blocked_nodes(project['trechos'])
    for chain in segments(project['trechos']):
        compatible = [(j, b) for j, b in enumerate(reels)
                      if b['condutor'] == chain[0]['condutor'] and b['tipo'] == chain[0]['tipo'] and available(b) > 0]
        max_cap = max((available(b) for _, b in compatible), default=Decimal(0))
        for a in range(len(chain)):
            if not start_allowed(chain[a],blocked):
                continue
            if a and chain[a-1]['corte_fim'] == 'PROIBIDO':
                continue
            for end in range(a, len(chain)):
                block = chain[a:end+1]
                size = length(block)
                if size > max_cap:
                    break
                if end_allowed(chain[end],blocked):
                    fixed = {r['fixa'] for r in block if r.get('fixa')}
                    for j, reel in compatible:
                        if (fixed and fixed != {reel['id']}) or size > available(reel):
                            continue
                        x = model.new_bool_var(f'x{len(candidates)}')
                        candidates.append((x, block, j, size))
                        for r in block:
                            coverage[r['id']].append(x)
                        by_reel[j].append((x, size))
                        if len(candidates) > 180000:
                            raise ValueError('Modelo com mais de 180 mil combinações. Planeje por parque/circuito ou fixe alocações já definidas.')
                if chain[end]['corte_fim'] == 'OBRIGATORIO':
                    break
    missing = [r['id'] for r in project['trechos'] if not coverage[r['id']]]
    if missing:
        raise ValueError('Sem lançamento viável para: ' + ', '.join(missing[:30]) + '. Verifique estoque, travessias, pontos de corte e bobinas fixadas.')
    seed_keys={(tuple(c['trechos']),c['bobina']) for c in seed}
    for x,rows,j,_ in candidates:
        if seed_keys:
            model.add_hint(x,int((tuple(r['id'] for r in rows),reels[j]['id']) in seed_keys))
    for variables in coverage.values():
        model.add_exactly_one(variables)
    stages = operations.objectives(model, candidates, by_reel, reels, available, project)
    selected = [c for c in candidates if (tuple(r['id'] for r in c[1]),reels[c[2]]['id']) in seed_keys] if seed else None
    results = []
    for index, (label, expression) in enumerate(stages):
        remaining = timeout - (time.monotonic() - start_time)
        if remaining <= 0:
            break
        model.minimize(expression)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max(.01, remaining / (len(stages)-index))
        solver.parameters.num_search_workers = 4
        solver.parameters.stop_after_first_solution = mode == 'rapido'
        status = solver.solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            if selected is not None:
                break
            if status == cp_model.INFEASIBLE:
                raise ValueError('Não existe alocação integral com este estoque e estes critérios.')
            raise ValueError('Nenhuma solução integral encontrada no tempo disponível. Aumente o tempo ou reduza o escopo; isso não comprova falta de cabo.')
        selected = [c for c in candidates if solver.value(c[0])]
        value = int(round(solver.objective_value))
        results.append(dict(criterio=label, valor=value, otimo=status==cp_model.OPTIMAL))
        if mode == 'rapido':
            break
        model.add(expression <= value)
    if selected is None:
        raise ValueError('Tempo esgotado antes da resolução. Aumente o tempo ou reduza o escopo.')
    cuts = [make_cut(rows, reels[j]['id'], i+1) for i, (_, rows, j, _) in enumerate(selected)]
    errors = validate(project, cuts)
    if errors:
        raise ValueError('Auditoria reprovada:\n' + '\n'.join(errors[:30]))
    return dict(cortes=cuts, fingerprint=fingerprint(project),
                status='Ótimo para a ordem de prioridades operacionais' if len(results)==len(stages) and all(r['otimo'] for r in results) else 'Solução viável; prioridades não comprovadamente ótimas',
                segundos=round(time.monotonic() - start_time, 2), combinacoes=len(candidates), etapas=results)



def consolidate_existing(project):
    cuts = []
    for chain in segments(project['trechos']):
        current = []
        for t in chain:
            if not t.get('bobina_original'):
                raise ValueError(f"{t['id']}: bobina original não informada.")
            if current and (current[-1]['bobina_original'] != t['bobina_original'] or current[-1]['corte_fim'] == 'OBRIGATORIO'):
                cuts.append(make_cut(current, current[0]['bobina_original'], len(cuts)+1))
                current = []
            current.append(t)
        if current:
            cuts.append(make_cut(current, current[0]['bobina_original'], len(cuts)+1))
    errors = validate(project, cuts)
    if errors:
        raise ValueError('\n'.join(errors[:50]))
    return dict(cortes=cuts, fingerprint=fingerprint(project), status='Alocação importada e validada', segundos=0)


def stock(project, cuts):
    used = Counter()
    for c in cuts:
        used[c['bobina']] += c['projeto']
    result = []
    for reel in project['bobinas']:
        remaining = available(reel) - dec(used[reel['id']])
        result.append(dict(bobina=reel['id'], condutor=reel['condutor'], nominal=reel['nominal'], real=reel.get('real'),
                           base=float(base(reel)), anterior=reel.get('utilizado', 0), reservado=used[reel['id']],
                           saldo=float(remaining), classificacao=('Histórico dentro do nominal; real a confirmar' if historical_nominal_exception(reel) else 'Não utilizada neste plano') if not used[reel['id']] else
                           operations.remainder_class(remaining, operations.settings(project))))
    return result
