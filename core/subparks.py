"""Consulta por trecho/fase, sem modificar ou completar os dados de origem."""
from collections import defaultdict
from html import escape
import re
from .engine import fingerprint, raw_length, segments, length, dec
from copy import deepcopy
from decimal import Decimal
import uuid

CIRCUITS = [f'C{i:02d}' for i in range(1, 35)]
LEVELS = ['1', '2', '3']
RESERVE_FIELDS = ['qte_caixas', 'sobra_caixa', 'qte_postes', 'sobra_poste', 'qte_turbinas', 'sobra_turbina', 'reserva_outros']


def circuit_id(value):
    value = str(value or '').strip().upper()
    match = re.fullmatch(r'C?0*(\d+)(?:\.0)?', value)
    return f'C{int(match.group(1)):02d}' if match else value


def launch_usage(project):
    """Metragem por bobina/parque, arredondada uma vez por lançamento contínuo."""
    usage = defaultdict(lambda: defaultdict(Decimal))
    def accumulate(reel, run):
        park = run[0]['parque']
        try:
            if any(any(not dec(r.get(f, 0)).is_finite() or dec(r.get(f, 0)) < 0 for f in ('linear', 'folga', 'reserva')) for r in run):
                raise ValueError('Metragem inválida')
            if usage[reel][park] is not None:
                usage[reel][park] += length(run)
        except (ValueError, TypeError, ArithmeticError):
            usage[reel][park] = None
    rows = [{**r, 'circuito':circuit_id(r['circuito'])} for r in project['trechos']]
    for chain in segments(rows):
        run = []
        reel = ''
        for row in chain:
            selected = row.get('bobina_original') or ''
            if run and (selected != reel or run[-1].get('corte_fim') == 'OBRIGATORIO'):
                if reel:
                    accumulate(reel, run)
                run = []
            reel = selected
            run.append(row)
        if run and reel:
            accumulate(reel, run)
    return usage


def replace_group(project, park, installation, old_ids, common, phase_rows):
    """Atualiza um único trecho A/B/C em cópia, sem apagar outros parques ou níveis."""
    candidate = deepcopy(project)
    if common.get('circuito') not in CIRCUITS or str(common.get('nivel')) not in LEVELS:
        raise ValueError('Selecione um circuito de C01 a C34 e um nível de 1 a 3.')
    for field in ('de', 'para', 'rota'):
        if not str(common.get(field) or '').strip():
            raise ValueError(f'Preencha {field}.')
    if common['de'].strip() == common['para'].strip():
        raise ValueError('As estruturas De e Para devem ser diferentes.')
    if installation not in ('AÉREO', 'SUBTERRÂNEO'):
        raise ValueError('Tipo de instalação inválido.')
    old = {r['id']: r for r in project['trechos'] if r['id'] in old_ids}
    if len(old) != len(old_ids) or any(r['parque'] != park or r['tipo'] != installation for r in old.values()):
        raise ValueError('O trecho mudou. Atualize a página e selecione-o novamente.')
    if len({r['fase'] for r in old.values()}) != len(old):
        raise ValueError('Corrija as fases duplicadas em Traçado antes de editar este grupo.')
    if len(phase_rows) != 3 or [r.get('fase') for r in phase_rows] != ['A', 'B', 'C']:
        raise ValueError('O trecho deve ter exatamente as fases A, B e C.')
    reels = {r['id']: r for r in project['bobinas']}
    replacement = []
    for phase_row in phase_rows:
        phase = phase_row['fase']
        previous = next((r for r in old.values() if r['fase'] == phase), {})
        row = {**previous, **common, **phase_row, 'id':previous.get('id', str(uuid.uuid4())),
               'parque':park, 'tipo':installation, 'nivel':str(common['nivel'])}
        row['circuito'] = circuit_id(row['circuito'])
        row['fixa'] = previous.get('fixa', '')
        if installation == 'SUBTERRÂNEO' and any(f in phase_row for f in RESERVE_FIELDS):
            for field in RESERVE_FIELDS:
                try:
                    value = dec(phase_row.get(field, 0))
                    if not value.is_finite() or value < 0 or (field.startswith('qte_') and value != value.to_integral_value()):
                        raise ValueError()
                    row[field] = float(value)
                except (ValueError, TypeError, ArithmeticError):
                    raise ValueError(f'Valor inválido em {field}, fase {phase}.') from None
            row['reserva'] = float(sum((dec(row[f]) for f in ('sobra_caixa', 'sobra_poste', 'sobra_turbina', 'reserva_outros')), Decimal(0)))
        for field in ('de', 'para', 'rota', 'condutor'):
            row[field] = str(row.get(field) or '').strip()
        if not row['condutor']:
            raise ValueError(f'Preencha o condutor da fase {phase}.')
        for field in ('linear', 'folga', 'reserva', 'ordem'):
            try:
                number = dec(row.get(field))
                if not number.is_finite() or number < 0:
                    raise ValueError()
                row[field] = float(number)
            except (ValueError, TypeError, ArithmeticError):
                raise ValueError(f'Valor inválido em {field}, fase {phase}.') from None
        if row['linear'] <= 0 or row['folga'] > 1 or row['ordem'] < 1:
            raise ValueError('Linear e ordem devem ser positivos; folga entre 0 e 1.')
        if row.get('corte_fim') not in ('PERMITIDO', 'PROIBIDO', 'OBRIGATORIO'):
            raise ValueError('Critério de corte inválido.')
        row['bobina_original'] = row.get('bobina_original') or ''
        reel = reels.get(row['bobina_original'])
        if row['bobina_original'] and (reel is None or reel['condutor'] != row['condutor'] or reel['tipo'] != installation):
            raise ValueError(f'Bobina incompatível ou não cadastrada na fase {phase}.')
        for other in project['trechos']:
            if other['id'] not in old_ids and all(str(other.get(k)) == str(row.get(k)) for k in ('parque', 'nivel', 'fase', 'tipo', 'rota')) and circuit_id(other['circuito']) == row['circuito'] and float(other['ordem']) == row['ordem']:
                raise ValueError('Já existe um trecho nessa ordem, circuito, nível e rota.')
        replacement.append(row)
    # Preserva as alocações dos outros trechos quando um plano válido vira cadastro editável.
    plan = project.get('plano')
    if plan and plan.get('fingerprint') == fingerprint(project):
        assigned = {ident:c['bobina'] for c in plan['cortes'] for ident in c['trechos']}
        for row in candidate['trechos']:
            if row['id'] in assigned:
                row['bobina_original'] = assigned[row['id']]
    candidate['trechos'] = [r for r in candidate['trechos'] if r['id'] not in old_ids] + replacement
    for row in candidate['trechos']:
        row['circuito'] = circuit_id(row['circuito'])
    candidate['plano'] = None
    candidate['criterios_confirmados'] = False
    return candidate


def natural(value):
    return tuple((1,int(v)) if v.isdigit() else (0,v) for v in re.split(r'(\d+)',str(value)))


def phase_groups(project, park, circuit=None, level=None, installation=None):
    grouped = defaultdict(list)
    for r in project['trechos']:
        if r['parque'] != park:
            continue
        if circuit is not None and circuit_id(r['circuito']) != circuit_id(circuit):
            continue
        if level is not None and str(r['nivel']) != level:
            continue
        if installation is not None and r['tipo'] != installation:
            continue
        r = {**r, 'circuito':circuit_id(r['circuito'])}
        k = tuple(str(r.get(f,'')) for f in ('tipo','circuito','nivel','rota','ordem','de','para'))
        grouped[k].append(r)
    plan = project.get('plano')
    current = bool(plan and plan.get('fingerprint') == fingerprint(project))
    assigned = {ident:c for c in plan['cortes'] for ident in c['trechos']} if current else {}
    groups, warnings = [], []
    for key, rows in sorted(grouped.items(),key=lambda pair:tuple(natural(v) for v in pair[0])):
        by_phase = defaultdict(list)
        for r in rows:
            by_phase[r['fase']].append(r)
        display = []
        label = f'{key[5]} → {key[6]} / circuito {key[1]} / nível {key[2]}'
        for phase in ('A','B','C'):
            matches = by_phase.pop(phase,[])
            if not matches:
                warnings.append(f'{label}: fase {phase} ausente no cadastro.')
                display.append({'fase':phase,'ausente':True})
            else:
                if len(matches)>1:
                    warnings.append(f'{label}: fase {phase} duplicada ({len(matches)} registros).')
                for r in matches:
                    c = assigned.get(r['id'])
                    try:
                        needed = float(raw_length([r]))
                    except (ValueError,TypeError,ArithmeticError,KeyError):
                        needed = None
                    display.append({**r,'ausente':False,'bobina':c['bobina'] if c else ('' if current else r.get('bobina_original','')),
                                    'corte':c['id'] if c else '', 'necessidade':needed})
        for phase,matches in by_phase.items():
            warnings.append(f'{label}: fase desconhecida {phase}.')
            display.extend({**r,'ausente':False,'bobina':r.get('bobina_original',''),'necessidade':None} for r in matches)
        groups.append(display)
    return groups, warnings, current


def table_html(groups, underground=False):
    columns=[('circuito','Circuito'),('nivel','Nível'),('fase','Fase'),('condutor','Condutor'),
             ('bobina','Bobina'),('de','De'),('para','Para'),('linear','Linear [m]'),
             ('folga','Folga [%]'),('reserva','Reserva [m]'),('necessidade','Necessidade sem arred. [m]'),
             ('corte','Lançamento'),('observacao','Observações')]
    if underground:
        index = next(i for i, (field, _) in enumerate(columns) if field == 'reserva')
        columns[index:index] = [('qte_caixas','Qte. caixas'), ('sobra_caixa','Sobra caixas [m]'),
            ('qte_postes','Qte. postes'), ('sobra_poste','Sobra postes [m]'),
            ('qte_turbinas','Qte. turbinas'), ('sobra_turbina','Sobra saída turbina [m]')]
    pieces=['''<style>
.rmt-phases{overflow:auto;max-height:650px;border:1px solid #b9c8d5;border-radius:8px;background:white;}
.rmt-phases table{border-collapse:collapse;width:100%;font-size:14px;color:#182c42;}
.rmt-phases th{position:sticky;top:0;background:#152b43;color:white;padding:12px;white-space:nowrap;text-align:left;z-index:1;}
.rmt-phases td{padding:10px 12px;border-bottom:1px solid #e2e8f0;white-space:nowrap;}
.rmt-phases tbody:nth-of-type(even){background:#f3f7fb;}
.rmt-phases tr.group-end td{border-bottom:4px double #58748f;}
.rmt-phases .phase{font-weight:700;color:#087e83;text-align:center;}
.rmt-phases .missing{color:#a63620;background:#fff4ed;}
</style><div class="rmt-phases"><table aria-label="Trechos por fase do subparque"><thead><tr>''']
    pieces.extend('<th>'+escape(title)+'</th>' for _,title in columns)
    pieces.append('</tr></thead>')
    for group in groups:
        pieces.append('<tbody>')
        for i,row in enumerate(group):
            css = 'group-end' if i==len(group)-1 else ''
            pieces.append(f'<tr class="{css}">')
            for field,_ in columns:
                value=row.get(field,'')
                if row.get('ausente'):
                    value = row['fase'] if field=='fase' else 'Fase não cadastrada' if field=='condutor' else '—'
                elif field in ('linear','reserva','necessidade','folga', *RESERVE_FIELDS):
                    try:
                        value = f'{float(value)*(100 if field=="folga" else 1):,.2f}'.replace(',','X').replace('.',',').replace('X','.')
                    except (TypeError,ValueError):
                        value='—'
                cls='missing' if row.get('ausente') else 'phase' if field=='fase' else ''
                pieces.append(f'<td class="{cls}">'+escape(str(value or '—'))+'</td>')
            pieces.append('</tr>')
        pieces.append('</tbody>')
    pieces.append('</table></div>')
    return ''.join(pieces)
