"""Resumo de bobinas: referência importada ou plano atual, sem dupla contagem."""
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import re
from .engine import base, dec, fingerprint
from .subparks import launch_usage


def park_id(value):
    s = re.sub(r'[-\s]', '', str(value)).upper()
    match = re.fullmatch(r'RSA0*(\d+)', s)
    return f'RSA{int(match.group(1)):02d}' if match else str(value)


def amount(value):
    try:
        n = dec(value)
        return n if n.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def summarize(project):
    plan = project.get('plano')
    current = bool(plan and plan.get('fingerprint') == fingerprint(project))
    usage = defaultdict(lambda: defaultdict(Decimal))
    active_parks = {park_id(t['parque']) for t in project.get('trechos', [])}
    if current:
        for c in plan['cortes']:
            usage[c['bobina']][park_id(c['parque'])] += dec(c['projeto'])
    else:
        for reel, values in launch_usage(project).items():
            for park, value in values.items():
                key = park_id(park)
                usage[reel][key] = (usage[reel][key] + value) if value is not None and usage[reel][key] is not None else None
    parks = {park_id(t['parque']) for t in project.get('trechos', [])}
    for reel in project['bobinas']:
        parks.update(park_id(k) for k in reel.get('consumo_importado_parques', {}))
        parks.update(park_id(k) for k in reel.get('parques_replanejados', []))
    parks = sorted(parks)
    ids = Counter(r['id'] for r in project['bobinas'])
    rows = []
    for reel in project['bobinas']:
        imported = {park_id(k): amount(v) for k,v in reel.get('consumo_importado_parques',{}).items()}
        scope = {park_id(k) for k in reel.get('parques_replanejados',[])}
        external = {k:v for k,v in imported.items() if k not in scope}
        values = dict(imported)
        replaced = active_parks | scope
        for k in replaced:
            values[k] = Decimal(0)
        for k,v in usage[reel['id']].items():
            values[k] = v
        previous = amount(reel.get('utilizado', 0))
        external_total = sum(external.values(),Decimal(0)) if all(v is not None for v in external.values()) else None
        difference = previous-external_total if previous is not None and external_total is not None else None
        # Ajustes manuais e projetos antigos ficam em uma coluna explícita.
        valid = (difference is not None and previous >= 0 and all(v is not None and v >= 0 for v in values.values()))
        total = sum(values.values(),Decimal(0))+difference if valid else None
        try:
            capacity = base(reel)
            if not capacity.is_finite() or capacity < 0:
                capacity = None
        except (InvalidOperation,ValueError,TypeError,KeyError):
            capacity = None
        balance = capacity-total if capacity is not None and total is not None else None
        state = 'Dados pendentes' if balance is None else 'Excedida' if balance < 0 else 'Esgotada' if balance == 0 else 'Com saldo'
        nominal = amount(reel.get('nominal'))
        if balance is not None and balance < 0 and reel.get('real') is None and nominal is not None and total <= nominal:
            state = 'Acima de 97%; dentro do nominal; real a confirmar'
        if ids[reel['id']] > 1:
            state += ' · ID duplicado'
        row = {'Romaneio':reel.get('romaneio',''), 'Bobina':reel['id'], 'Condutor':reel.get('condutor',''), 'Tipo':reel.get('tipo','')}
        row.update({k:float(values.get(k,0)) if values.get(k,0) is not None else None for k in parks})
        row.update({'Ajuste / sem parque [m]':float(difference) if difference is not None else None,
                    'Total utilizado [m]':float(total) if total is not None else None,
                    'Saldo disponível [m]':float(balance) if balance is not None else None,
                    'Base da bobina [m]':float(capacity) if capacity is not None else None,
                    'Nominal [m]':reel.get('nominal'), 'Real confirmada [m]':reel.get('real'),
                    'Origem da metragem':'Real confirmada' if reel.get('real') is not None else 'Nominal × 97%',
                    'Situação':state})
        rows.append(row)
    return rows, parks, current


def row_style(row):
    if 'real a confirmar' in str(row.get('Situação','')) and 'duplicado' not in str(row.get('Situação','')):
        return ['color: #92400e; background-color: #fffbeb'] * len(row)
    balance = row.get('Saldo disponível [m]')
    if balance is not None and balance < 0:
        return ['color: #b91c1c; background-color: #fff1f2; font-weight: 600'] * len(row)
    if 'pendente' in str(row.get('Situação','')).lower() or 'duplicado' in str(row.get('Situação','')).lower():
        return ['color: #92400e; background-color: #fffbeb'] * len(row)
    return [''] * len(row)
