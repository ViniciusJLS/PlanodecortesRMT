"""Exportação XLSX portátil por OOXML, sem macros ou vínculos externos.

Os valores calculados são um instantâneo do plano validado. Esta camada não
recalcula distâncias e não usa as metragens arredondadas do controle legado.
"""
import io
import re
from collections import Counter, defaultdict
from datetime import datetime
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED
from .engine import stock, fingerprint, validate

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'


def column(n):
    result = ''
    while n:
        n, rem = divmod(n-1, 26)
        result = chr(65+rem) + result
    return result


def cell(value, row, col, style=0):
    ref = f'{column(col)}{row}'
    if value is None:
        return f'<c r="{ref}" s="{style}"/>'
    if isinstance(value, (int, float)):
        return f'<c r="{ref}" s="{style}"><v>{value}</v></c>'
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', str(value))
    return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{escape(cleaned)}</t></is></c>'


def worksheet(title, metadata, headers, records, widths):
    n = len(headers)
    rows = [f'<row r="1" ht="32" customHeight="1">{cell(title,1,1,1)}</row>',
            f'<row r="2" ht="24" customHeight="1">{cell(metadata,2,1,5)}</row>',
            '<row r="4" ht="32" customHeight="1">' + ''.join(cell(v,4,i+1,2) for i,v in enumerate(headers)) + '</row>']
    for r, record in enumerate(records, 5):
        rows.append(f'<row r="{r}" ht="30" customHeight="1">' + ''.join(cell(v,r,c+1,3 if isinstance(v,(int,float)) else 4) for c,v in enumerate(record)) + '</row>')
    last = max(4, len(records)+4)
    cols = ''.join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i,w in enumerate(widths,1))
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="{NS}"><dimension ref="A1:{column(n)}{last}"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="4" topLeftCell="A5" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><sheetFormatPr defaultRowHeight="24"/><cols>{cols}</cols><sheetData>{''.join(rows)}</sheetData><autoFilter ref="A4:{column(n)}{last}"/><mergeCells count="2"><mergeCell ref="A1:{column(n)}1"/><mergeCell ref="A2:{column(n)}2"/></mergeCells><printOptions horizontalCentered="1"/><pageMargins left="0.25" right="0.25" top="0.4" bottom="0.4" header="0.2" footer="0.2"/><pageSetup paperSize="9" orientation="landscape" fitToWidth="1" fitToHeight="0"/><headerFooter><oddFooter>&amp;LPlano de corte RMT&amp;RPágina &amp;P de &amp;N</oddFooter></headerFooter></worksheet>'''


STYLES = f'''<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="{NS}">
<numFmts count="1"><numFmt numFmtId="164" formatCode="#,##0.00"/></numFmts>
<fonts count="4"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="18"/><color rgb="FF152B43"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font><font><sz val="10"/><color rgb="FF536579"/><name val="Calibri"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF152B43"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="2"><border/><border><bottom style="thin"><color rgb="FFE1E7ED"/></bottom></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="6"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="2" fillId="2" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1"/><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0"/></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'''


def workbook(sheets):
    stream = io.BytesIO()
    rel_ns = 'http://schemas.openxmlformats.org/package/2006/relationships'
    with ZipFile(stream, 'w', ZIP_DEFLATED) as z:
        overrides = ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,len(sheets)+1))
        z.writestr('[Content_Types].xml', f'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>{overrides}</Types>')
        z.writestr('_rels/.rels', f'<Relationships xmlns="{rel_ns}"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        names, relationships, defined = [], [], []
        seen = set()
        for i, (name, title, meta, headers, records, widths) in enumerate(sheets, 1):
            name = re.sub(r'[\[\]:*?/\\]', '-', name)[:28]
            original = name
            while name in seen:
                name = original[:24] + f' {i}'
            seen.add(name)
            names.append(f'<sheet name="{escape(name, {chr(34): "&quot;"})}" sheetId="{i}" r:id="rId{i}"/>')
            relationships.append(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>')
            defined.append(f'<definedName name="_xlnm.Print_Titles" localSheetId="{i-1}">\'{escape(name.replace(chr(39), chr(39)*2))}\'!$1:$4</definedName>')
            z.writestr(f'xl/worksheets/sheet{i}.xml', worksheet(title, meta, headers, records, widths))
        z.writestr('xl/workbook.xml', f'<workbook xmlns="{NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><bookViews><workbookView/></bookViews><sheets>{"".join(names)}</sheets><definedNames>{"".join(defined)}</definedNames></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', f'<Relationships xmlns="{rel_ns}">{"".join(relationships)}<Relationship Id="styles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        z.writestr('xl/styles.xml', STYLES)
    return stream.getvalue()


def export(project, kind):
    plan = project.get('plano')
    if not plan or plan['fingerprint'] != fingerprint(project):
        raise ValueError('Gere ou valide novamente o plano após alterar os dados.')
    cuts = plan['cortes']
    issues = validate(project, cuts)
    if issues:
        raise ValueError('\n'.join(issues[:20]))
    meta = f"{project['nome']} | {project['codigo']} | Revisão {project['revisao']} | {datetime.now():%d/%m/%Y} | Planejamento"
    inventory = stock(project, cuts)
    sheets = []
    def add(name, title, headers, records, widths):
        sheets.append((name, title, meta, headers, records, widths))
    add('Resumo', 'RESUMO DAS BOBINAS UTILIZADAS',
        ['Bobina', 'Condutor', 'Consumo neste documento [m]', 'Comprimento nominal [m]', 'Metragem real [m]', 'Base [m]', 'Consumo anterior [m]', 'Saldo após plano [m]', 'Classificação'],
        [[r[k] for k in ('bobina','condutor','reservado','nominal','real','base','anterior','saldo','classificacao')] for r in inventory if r['reservado']],
        [23,36,20,19,18,16,19,20,25])
    if kind == 'entregavel':
        groups = defaultdict(list)
        for c in cuts:
            groups[(c['parque'], c['circuito'], c['tipo'])].append(c)
        for (park, circuit, typ), values in groups.items():
            values.sort(key=lambda c: (c['de'], c['para'], c['nivel'], c['fase']))
            add(f'{park} {circuit} {typ[:3]}', f'PLANO DE CORTE — {park} / {circuit}',
                ['Condutor','Bobina','Circuito','Fase','Nível','De','Para','Distância linear [m]','Acréscimos sem arredondar [m]','Distância de projeto [m]'],
                [[c[k] for k in ('condutor','bobina','circuito','fase','nivel','de','para','linear','acrescimo','projeto')] for c in values],
                [34,23,12,9,9,25,25,17,20,18])
    else:
        assigned = {ident:c for c in cuts for ident in c['trechos']}
        add('Trechos', 'CONTROLE DETALHADO DOS TRECHOS',
            ['Trecho','Parque','Circuito','Nível','Fase','Condutor','De','Para','Linear [m]','Folga (fração)','Reserva [m]','Corte','Bobina','Corte no fim'],
            [[r['id'],r['parque'],r['circuito'],r['nivel'],r['fase'],r['condutor'],r['de'],r['para'],r['linear'],r['folga'],r['reserva'],assigned[r['id']]['id'],assigned[r['id']]['bobina'],r['corte_fim']] for r in project['trechos']],
            [23,15,12,9,9,34,25,25,16,16,16,12,23,18])
        add('Lançamentos','CONSUMO POR LANÇAMENTO CONTÍNUO',
            ['Corte','Parque','Circuito','Nível','Fase','Bobina','De','Para','Linear [m]','Acréscimos [m]','Projeto [m]'],
            [[c[k] for k in ('id','parque','circuito','nivel','fase','bobina','de','para','linear','acrescimo','projeto')] for c in cuts],
            [12,15,12,9,9,23,25,25,16,16,16])
        add('Estoque','ESTOQUE E RESERVAS DO PLANO',
            ['Bobina','Condutor','Nominal [m]','Real [m]','Base [m]','Anterior [m]','Reservado [m]','Saldo [m]','Classificação'],
            [[r[k] for k in ('bobina','condutor','nominal','real','base','anterior','reservado','saldo','classificacao')] for r in inventory],
            [23,36,16,16,16,16,16,16,26])
    add('Critérios','CRITÉRIOS E RASTREABILIDADE', ['Regra','Valor'],
        [['Metragem das bobinas','Real informada; na ausência, nominal × 0,97'],
         ['Distância de projeto','Soma de linear × (1 + folga) e reservas; arredondamento para cima uma vez por lançamento'],
         ['Reservas','Valores por trecho; cadastre cada reserva física uma única vez por condutor'],
         ['Status do cálculo',plan['status']], ['Sobra mínima reutilizável [m]',project['criterios']['sobra_minima']],
         ['Identificação dos dados',plan['fingerprint']], ['Consumo','Reserva de planejamento; não constitui baixa de execução']], [37,110])
    return workbook(sheets)


def export_subpark(project, park):
    """Excel final do subparque, com alocações e saldo do estoque da obra."""
    plan=project.get('plano')
    if not plan or plan.get('fingerprint') != fingerprint(project):
        raise ValueError('Calcule e valide o plano antes de baixar o Excel final.')
    issues=validate(project,plan['cortes'])
    if issues:
        raise ValueError('\n'.join(issues[:20]))
    cuts=[c for c in plan['cortes'] if c['parque']==park]
    if not cuts:
        raise ValueError('Este subparque não possui lançamentos no plano.')
    assigned={ident:c for c in cuts for ident in c['trechos']}
    rows=[r for r in project['trechos'] if r['id'] in assigned]
    from .subparks import natural
    rows.sort(key=lambda r:tuple(natural(r.get(k,'')) for k in ('tipo','circuito','nivel','rota','ordem','fase')))
    meta=f"Obra: {project['nome']} | Subparque: {park} | Revisão {project['revisao']} | {plan['status']}"
    detailed=[[r['circuito'],r['nivel'],r['fase'],r['tipo'],r['condutor'],assigned[r['id']]['bobina'],
        r['de'],r['para'],r['linear'],r['folga'],r['reserva'],assigned[r['id']]['id'],r.get('origem',''),r.get('observacao',''),
        r.get('corte_fim','PERMITIDO'),r.get('restricao_estrutura','')] for r in rows]
    consumed=Counter()
    for cut in cuts:consumed[cut['bobina']]+=cut['projeto']
    inventory=[r for r in stock(project,plan['cortes']) if consumed[r['bobina']]]
    sheets=[('PLANO DE CORTE','TRECHOS E BOBINAS ALOCADAS',meta,
        ['Circuito','Nível','Fase','Tipo','Condutor','Bobina alocada','De','Para','Distância linear [m]',
         'Folga (fração)','Reserva [m]','Lançamento','Origem na referência','Observações','Corte no fim','Estrutura sem corte'],detailed,
        [12,9,9,18,34,24,27,27,22,18,16,16,44,40,18,34]),
        ('LANÇAMENTOS','LANÇAMENTOS CONTÍNUOS',meta,
        ['Lançamento','Circuito','Nível','Fase','Tipo','Condutor','Bobina','De','Para','Linear [m]','Acréscimos [m]','Projeto [m]'],
        [[c[k] for k in ('id','circuito','nivel','fase','tipo','condutor','bobina','de','para','linear','acrescimo','projeto')] for c in cuts],
        [16,12,9,9,18,34,24,27,27,18,18,18]),
        ('RESUMO_BOBINAS','BOBINAS UTILIZADAS NESTE SUBPARQUE',meta,
        ['Bobina','Condutor','Base [m]','Anterior [m]','Uso neste subparque [m]','Reservado em toda obra [m]','Saldo na obra [m]'],
        [[r['bobina'],r['condutor'],r['base'],r['anterior'],consumed[r['bobina']],r['reservado'],r['saldo']] for r in inventory],
        [24,34,18,18,25,28,23]),
        ('CRITÉRIOS','CRITÉRIOS DO RESULTADO',meta,['Regra','Valor'],
        [['Cálculo de projeto','Soma das distâncias lineares com folgas e reservas; arredondamento apenas por lançamento contínuo'],
         ['Distância por trecho','A coluna Linear mantém o valor da referência; a metragem de corte consta em LANÇAMENTOS'],
         ['Saldo','Considera o consumo anterior e as reservas de todos os subparques desta obra'],
         ['Estruturas sem corte','Azul ou esforço 1000 em gaveta não permitem início/fim de bobina. A distância positiva do vão permanece no cálculo.'],
         ['Dados do plano',plan['fingerprint']],['Status',plan['status']]], [35,110])]
    return workbook(sheets)
