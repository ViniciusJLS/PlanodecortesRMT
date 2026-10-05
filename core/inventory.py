"""Resumo de bobinas: referência importada ou plano atual, sem dupla contagem."""
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import re
from .engine import base, dec, fingerprint


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
    if current:
        for c in plan['cortes']:
            usage[c['bobina']][park_id(c['parque'])] += dec(c['projeto'])
    parks = {park_id(t['parque']) for t in project.get('trechos', [])}
    for reel in project['bobinas']:
        parks.update(park_id(k) for k in reel.get('consumo_importado_parques', {}))
    parks = sorted(parks)
    ids = Counter(r['id'] for r in project['bobinas'])
    rows = []
    for reel in project['bobinas']:
        imported = {park_id(k): amount(v) for k,v in reel.get('consumo_importado_parques',{}).items()}
        scope = {park_id(k) for k in reel.get('parques_replanejados',[])}
        external = {k:v for k,v in imported.items() if k not in scope}
        values = dict(external)
        if current:
            for k in scope:
                values[k] = Decimal(0)
            for k,v in usage[reel['id']].items():
                values[k] = (values.get(k, Decimal(0)) + v) if values.get(k, 0) is not None else None
        else:
            values.update({k:v for k,v in imported.items() if k in scope})
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
    balance = row.get('Saldo disponível [m]')
    if balance is not None and balance < 0:
        return ['color: #b91c1c; background-color: #fff1f2; font-weight: 600'] * len(row)
    if 'pendente' in str(row.get('Situação','')).lower() or 'duplicado' in str(row.get('Situação','')).lower():
        return ['color: #92400e; background-color: #fffbeb'] * len(row)
    return [''] * len(row)
