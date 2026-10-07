"""Visualização aérea no formato RSA-01; não altera os dados do lançamento."""
from collections import defaultdict
from decimal import Decimal
from .engine import base, dec, fingerprint
from .subparks import launch_usage, natural, table_html


def number(value):
    if value is None:return '—'
    try:
        return f'{float(value):,.2f}'.replace(',','X').replace('.',',').replace('X','.')
    except (TypeError,ValueError,ArithmeticError):return '—'


def balances(project):
    """Saldo da bobina na obra: consumo anterior e todos os lançamentos atuais."""
    plan=project.get('plano')
    used=defaultdict(Decimal)
    pending=set()
    if plan and plan.get('fingerprint')==fingerprint(project):
        for c in plan['cortes']:used[c['bobina']]+=dec(c['projeto'])
    else:
        for reel,parks in launch_usage(project).items():
            for value in parks.values():
                if value is None:pending.add(reel)
                else:used[reel]+=value
    result={}
    for reel in project['bobinas']:
        try:
            result[reel['id']]=None if reel['id'] in pending else base(reel)-dec(reel.get('utilizado',0))-used[reel['id']]
        except (ValueError,TypeError,ArithmeticError,KeyError):result[reel['id']]=None
    return result


def rows_and_columns(project, groups):
    levels=['1','2']
    if any(str(r.get('nivel'))=='3' for g in groups for r in g if not r.get('ausente')):levels.append('3')
    columns=[]
    for level in levels:
        columns.extend([(f'descricao_{level}',f'DESCRIÇÃO (NIVEL {level})'),
            (f'bobina_{level}',f'BOBINA (NIVEL {level})'),(f'circuito_{level}',f'CIRCUITO (NIVEL {level})')])
    columns.extend([('fase','FASE'),('tipo','TIPO'),('de','DE'),('para','PARA'),('distancia_projeto','DISTÂNCIA PROJETO')])
    columns.extend((f'sobra_{level}',f'SOBRA BOBINA {level}') for level in levels)
    columns.append(('observacao','OBSERVAÇÕES'))
    physical=defaultdict(lambda:defaultdict(list))
    # Alinha níveis que têm o mesmo vão, ordem e rota. Circuitos diferentes
    # dentro do mesmo nível ocupam grupos separados, sem descartar registros.
    for group in groups:
        first=next((r for r in group if not r.get('ausente')),None)
        if first is None:continue
        try:order=format(dec(first['ordem']).normalize(),'f')
        except (ValueError,TypeError,ArithmeticError,KeyError):order=str(first.get('ordem',''))
        key=(str(first.get('rota','')),str(first.get('bloco_tramo','')),order,str(first['de']),str(first['para']))
        physical[key][str(first['nivel'])].append(group)
    remaining=balances(project)
    output=[]
    for key,by_level in sorted(physical.items(),key=lambda x:tuple(natural(v) for v in x[0])):
        for index in range(max(map(len,by_level.values()))):
            selected={level:by_level[level][index] for level in levels if index<len(by_level.get(level,[]))}
            # Fases duplicadas são exibidas, além da pendência já indicada na página.
            copies=max(sum(r.get('fase')==phase for r in group) for group in selected.values() for phase in 'ABC')
            for copy in range(copies):
                rendered=[]
                for phase in 'ABC':
                    display=dict(fase=phase,tipo='AÉREO',de=key[3],para=key[4])
                    values={}
                    notes=[]
                    for level,group in selected.items():
                        matches=[r for r in group if r.get('fase')==phase]
                        r=matches[copy] if copy<len(matches) else None
                        if not r or r.get('ausente'):
                            display[f'descricao_{level}']='Fase não cadastrada'
                            continue
                        display.update({f'descricao_{level}':r['condutor'],f'bobina_{level}':r.get('bobina',''),f'circuito_{level}':r['circuito'],
                            f'sobra_{level}':number(remaining.get(r.get('bobina')))})
                        values[level]=r.get('necessidade')
                        if r.get('observacao'):notes.append(str(r['observacao']))
                        if r.get('restricao_estrutura'):notes.append('Estrutura sem corte: '+str(r['restricao_estrutura']))
                        elif r.get('corte_fim')=='PROIBIDO':notes.append('Corte proibido em '+str(r['para']))
                    distinct={v for v in values.values()}
                    display['distancia_projeto']=number(next(iter(distinct))) if len(distinct)==1 else ' / '.join(f'N{level}: {number(v)}' for level,v in values.items())
                    display['observacao']='; '.join(dict.fromkeys(notes))
                    rendered.append(display)
                output.append(rendered)
    return columns,output


def aerial_table_html(project,groups):
    columns,rows=rows_and_columns(project,groups)
    return table_html(rows,columns=columns)
