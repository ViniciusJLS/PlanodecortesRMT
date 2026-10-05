"""Consulta por trecho/fase, sem modificar ou completar os dados de origem."""
from collections import defaultdict
from html import escape
import re
from .engine import fingerprint, raw_length


def natural(value):
    return tuple((1,int(v)) if v.isdigit() else (0,v) for v in re.split(r'(\d+)',str(value)))


def phase_groups(project, park, circuit=None, level=None, installation=None):
    grouped = defaultdict(list)
    for r in project['trechos']:
        if r['parque'] != park:
            continue
        if circuit is not None and str(r['circuito']) != circuit:
            continue
        if level is not None and str(r['nivel']) != level:
            continue
        if installation is not None and r['tipo'] != installation:
            continue
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


def table_html(groups):
    columns=[('circuito','Circuito'),('nivel','Nível'),('fase','Fase'),('condutor','Condutor'),
             ('bobina','Bobina'),('de','De'),('para','Para'),('linear','Linear [m]'),
             ('folga','Folga [%]'),('reserva','Reserva [m]'),('necessidade','Necessidade sem arred. [m]'),
             ('corte','Lançamento'),('observacao','Observações')]
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
                elif field in ('linear','reserva','necessidade','folga'):
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
