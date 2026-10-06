"""Converte a sequência I/L do AUX TRAMO em trechos explícitos por fase."""
import math
from .importer import text, norm, number
from .reference import parse_reference


def is_aux(headers):
    return len(headers)>=12 and norm(headers[8])=='POSTE' and norm(headers[11])=='DISTANCIA TRAMO'


def aux_bounds(data):
    header = next((i for i,row in enumerate(data,1) if is_aux(row)), None)
    if header is None:
        raise ValueError('Cabeçalho POSTE em I e DISTÂNCIA TRAMO em L não encontrado.')
    used = [i for i,row in enumerate(data,1) if i>header and len(row)>8 and text(row[8])]
    if not used:
        raise ValueError('Nenhum poste na coluna I.')
    return header,used[0],used[-1]


def parse_aux(data, config, start, end):
    """L da linha Para mede o vão entre I da linha anterior e I da atual."""
    if start<1 or end<start or end>len(data):
        raise ValueError('Intervalo inválido.')
    previous=None
    block=0
    physical=[]
    errors=[]
    boundaries=0
    for line in range(start,end+1):
        raw=data[line-1]
        pole=text(raw[8]) if len(raw)>8 else ''
        distance=raw[11] if len(raw)>11 else None
        if not pole:
            previous=None
            continue
        if norm(pole)=='POSTE':
            previous=None
            continue
        value=number(distance)
        if value is None or value<0 or not math.isfinite(value):
            errors.append(f'Linha {line}: distância L inválida ou fórmula sem resultado salvo.')
            previous=None
            continue
        placeholder=pole.upper() in ('P.','P','-','—') or pole.startswith('#')
        if placeholder:
            if value!=0:
                errors.append(f'Linha {line}: poste incompleto com distância positiva.')
            previous=None
            boundaries+=1
            continue
        if value==0:
            block+=1
            boundaries+=1
            previous=(pole,line)
            continue
        if previous is None:
            errors.append(f'Linha {line}: distância positiva sem poste anterior no intervalo. Inclua a linha de início do tramo.')
            continue
        if previous[0]==pole:
            errors.append(f'Linha {line}: mesmo poste nas duas extremidades.')
        else:
            physical.append((previous[0],pole,value,previous[1],line,block))
        previous=(pole,line)
    if errors:
        raise ValueError('\n'.join(errors[:30]))
    if not physical:
        raise ValueError('Nenhum vão positivo entre postes foi encontrado no intervalo.')
    result=[]
    offset=0
    # Reusa a validação de números, parâmetros e geração A/B/C da importação normal.
    for block_id in sorted({r[5] for r in physical}):
        records=[r for r in physical if r[5]==block_id]
        route=f"{config['rota']} · TRAMO {block_id}"
        rows,_=parse_reference([[r[0],r[1],r[2]] for r in records],dict(de=0,para=1,linear=2),
            {**config,'rota':route},1,len(records),'expand')
        for i, record in enumerate(records):
            for row in rows[i*3:i*3+3]:
                row['origem']=f"{config['sheet']}!I{record[3]}→I{record[4]} / L{record[4]}"
                row['referencia_de_linha']=record[3]
                row['referencia_para_linha']=record[4]
                row['referencia_distancia_linha']=record[4]
                # O escopo continua sendo a rota escolhida; separação física via identificador de bloco.
                row['rota']=config['rota']
                row['bloco_tramo']=str(block_id)
                row['ordem']=offset+i+1
        result.extend(rows)
        offset+=len(records)
    return result,boundaries
