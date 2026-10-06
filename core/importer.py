"""Leitura dos controles legados e de CSVs normalizados; nenhuma edição da origem."""
import io
import re
import unicodedata
from collections import defaultdict
import openpyxl


def text(v):
    if v is None:
        return ''
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return re.sub(r'\s+', ' ', str(v)).strip()


def norm(v):
    return ''.join(c for c in unicodedata.normalize('NFD', text(v).upper()) if unicodedata.category(c) != 'Mn')


def number(v, default=None):
    if v is None or v == '':
        return default
    if isinstance(v, str):
        v = v.strip()
        if ',' in v:
            v = v.replace('.', '').replace(',', '.')
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def list_parks(content):
    w = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    result = [s for s in w.sheetnames if re.fullmatch(r'RSA[- ]?\d+', s, re.I)]
    w.close()
    return result


def import_control(content, selected):
    w = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=False)
    wf = openpyxl.load_workbook(io.BytesIO(content), data_only=False, read_only=True)
    rows, reels, warnings = [], [], []
    missing = [s for s in selected if s not in w.sheetnames]
    if missing:
        raise ValueError('Abas ausentes: ' + ', '.join(missing))
    standards = {}
    if 'RESUMO_BOBINAS' not in w.sheetnames:
        raise ValueError('Este importador espera a aba RESUMO_BOBINAS do controle enviado. Para outros modelos, use CSV.')
    source = list(w['RESUMO_BOBINAS'].values)
    formulas = list(wf['RESUMO_BOBINAS'].values)
    for r in source[:9]:
        if len(r) > 4 and isinstance(r[3], (int, float)) and text(r[1]):
            standards[text(r[1])] = float(r[3])
    header_index = next((i for i, r in enumerate(source) if any(norm(v) == 'BOBINA' for v in r)), None)
    if header_index is None:
        raise ValueError('Cabeçalho do estoque não encontrado.')
    headers = {norm(v): j for j, v in enumerate(source[header_index]) if v is not None}
    def col(fragment):
        return next((j for h, j in headers.items() if fragment in h), None)
    id_col, cable_col, type_col = col('BOBINA'), col('CONDUTOR'), col('TIPO')
    total_col, full_col = col('QUANTIDADE UTILIZADA'), col('BOBINA CHEIA')
    excluded = {norm(s).replace('-', '').replace(' ', '') for s in selected}
    for index in range(header_index + 1, len(source)):
        r = source[index]
        ident = text(r[id_col])
        if not ident or ident.startswith('#'):
            continue
        cable = text(r[cable_col])
        if not cable:
            continue
        past = 0.0
        unknown = False
        park_usage = {}
        # Somente parques fora do escopo permanecem como consumo anterior.
        for h, j in headers.items():
            park_key = h.replace('-', '').replace(' ', '')
            if re.fullmatch(r'RSA\d+', park_key):
                val = number(r[j])
                park_usage[park_key] = val if r[j] is not None else 0.0
                if park_key in excluded:
                    continue
                if val is None and r[j] is not None:
                    unknown = True
                past += val or 0
        nominal = standards.get(cable)
        real = None
        f = formulas[index][full_col] if full_col is not None else None
        if nominal is None:
            warnings.append(f'{ident}: comprimento nominal não localizado; preencha antes de calcular.')
            nominal = 0
        if not (isinstance(f, str) and f.startswith('=')) and number(r[full_col]) is not None:
            warnings.append(f'{ident}: BOBINA CHEIA tem valor manual ({r[full_col]} m). Confirme se é metragem real na tela Bobinas; foi mantida a base nominal de 97%.')
        if unknown:
            warnings.append(f'{ident}: consumo externo com erro Excel; importação bloqueada até corrigir a origem.')
            past = -1
        reels.append(dict(id=ident, condutor=cable, tipo=text(r[type_col]), nominal=nominal,
                          real=real, utilizado=past, origem=f'RESUMO_BOBINAS!{index+1}',
                          romaneio=text(r[col('ROMANEIO')]) if col('ROMANEIO') is not None else '',
                          consumo_importado_parques=park_usage,
                          parques_replanejados=sorted(excluded)))
    count = defaultdict(int)
    for name in selected:
        header = None
        block = 0
        from openpyxl.utils.cell import range_boundaries
        bounds = [range_boundaries(t.ref) for t in w[name].tables.values()]
        for i, r in enumerate(w[name].values, 1):
            if bounds and not any(lo <= i <= hi for _,lo,_,hi in bounds):
                continue
            if any(norm(v) == 'DISTANCIA LINEAR' for v in r):
                header = {norm(v): j for j, v in enumerate(r) if v is not None}
                block += 1
                continue
            if header is None:
                continue
            def get(label):
                j = header.get(label)
                return r[j] if j is not None and j < len(r) else None
            phase = text(get('FASE'))
            if phase not in ('A', 'B', 'C'):
                continue
            start, end = text(get('DE')), text(get('PARA'))
            dist = number(get('DISTANCIA LINEAR'))
            if not start or not end or dist is None or start.startswith('#') or end.startswith('#'):
                warnings.append(f'{name}!{i}: linha incompleta ou com erro Excel; corrija a origem. Registro mantido para validação.')
            for level in (1, 2, 3):
                cable = text(get(f'DESCRICAO (NIVEL {level})'))
                if not cable and level == 1:
                    cable = text(get('DESCRICAO'))
                if not cable:
                    continue
                reel = text(get(f'BOBINA (NIVEL {level})')) or (text(get('BOBINA')) if level == 1 else '')
                circuit = text(get(f'CIRCUITO (NIVEL {level})')) or text(get('CIRCUITO'))
                # Blocos subterrâneos podem não repetir o circuito: exigir revisão.
                typ = text(get('TIPO'))
                fraction = number(get('FOLGA DESNIVEL'))
                if fraction is None:
                    fraction = .02 if norm(typ) == 'SUBTERRANEO' else .05
                    warnings.append(f'{name}!{i}: folga ausente; aplicado padrão de {fraction:.0%}, sujeito à revisão.')
                reserves = [get(k) for k in ('SOBRA CAIXA', 'SOBRA POSTE', 'SOBRA SAIDA TURBINA')]
                bad_reserve = any(v is not None and number(v) is None for v in reserves)
                reserve = -1 if bad_reserve else sum(number(v, 0) for v in reserves)
                route = f'B{block}'
                count[(name, circuit, level, phase, route)] += 1
                obs = text(get('OBSERVACOES'))
                rows.append(dict(id=f'{name}-{i}-N{level}', parque=name, circuito=circuit, nivel=str(level),
                                 fase=phase, tipo=typ, condutor=cable, rota=route,
                                 ordem=count[(name, circuit, level, phase, route)], de=start, para=end,
                                 linear=dist if dist is not None else -1, folga=fraction, reserva=reserve,
                                 corte_fim='PERMITIDO', fixa='', bobina_original=reel,
                                 observacao=obs, origem=f'{name}!{i}',
                                 qte_caixas=number(get('QTE. CAIXAS'), 0), sobra_caixa=number(get('SOBRA CAIXA'), 0),
                                 qte_postes=number(get('QTE. POSTE'), 0), sobra_poste=number(get('SOBRA POSTE'), 0),
                                 qte_turbinas=number(get('QTE. TURBINA'), 0), sobra_turbina=number(get('SOBRA SAIDA TURBINA'), 0),
                                 reserva_outros=0))
    w.close()
    wf.close()
    warnings.insert(0, 'Os cortes foram importados como PERMITIDO. Confirme amarrações e travessias na tela Critérios antes de otimizar; a marca TRAV não determina sozinha os limites da travessia.')
    warnings.insert(1, 'O consumo dos parques selecionados foi retirado do histórico para evitar desconto duplicado. Não use este modo para trechos já executados que precisam permanecer no histórico.')
    return rows, reels, warnings


def import_csv(content, kind):
    import pandas as pd
    df = pd.read_csv(io.BytesIO(content), sep=None, engine='python', dtype=str, keep_default_na=False)
    records = df.to_dict('records')
    required = ['id', 'condutor', 'tipo', 'nominal'] if kind == 'bobinas' else ['id', 'parque', 'circuito', 'nivel', 'fase', 'condutor', 'tipo', 'de', 'para', 'linear', 'ordem']
    for field in required:
        if field not in df.columns:
            raise ValueError(f'Coluna obrigatória ausente: {field}')
    for r in records:
        numeric_fields = ('nominal','real','utilizado') if kind == 'bobinas' else ('linear','ordem','folga','reserva')
        for field in numeric_fields:
            if r.get(field) not in (None, '') and number(r[field]) is None:
                raise ValueError(f"{r.get('id')}: valor numérico inválido em {field}: {r[field]}")
        if kind == 'bobinas':
            for k in ('nominal', 'utilizado'):
                r[k] = number(r.get(k), 0)
            r['real'] = number(r.get('real'))
        else:
            for k, default in [('linear', -1), ('ordem', 0), ('folga', .05), ('reserva', 0)]:
                r[k] = number(r.get(k), default)
            for k, default in [('rota', 'Principal'), ('corte_fim', 'PERMITIDO'), ('fixa', ''), ('bobina_original', ''), ('observacao', '')]:
                r[k] = r.get(k) or default
    return records
