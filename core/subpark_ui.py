"""Edição dos lançamentos por subparque, com persistência no projeto."""
import json
import sqlite3
import pandas as pd
import streamlit as st
from . import project as projects
from .subparks import CIRCUITS, LEVELS, RESERVE_FIELDS, natural, phase_groups, table_html, replace_group
from .reference_ui import new_park, render_reference, render_optimization
from .conductor_ui import selection
from .conductors import options as conductor_options
from .aerial_table import aerial_table_html


def open_summary():
    st.session_state.work_area = 'Resumo de bobinas'


def render(project):
    st.caption('Selecione o subparque. Salve cada trecho antes de trocar de seleção; os lançamentos salvos alimentam o Resumo de bobinas.')
    new_park(project)
    parks = sorted({r['parque'] for r in project['trechos']} | set(project.get('subparques', [])), key=natural)
    if not parks:
        st.info('Cadastre um subparque acima para importar seu Excel de referência.')
        return
    prefix = f"subpark_{project['id']}"
    park = st.selectbox('Subparque', parks, key=prefix+'_park')
    render_reference(project, park)
    a, b = st.columns(2)
    circuit = a.selectbox('Filtrar circuito', ['Todos']+CIRCUITS, key=prefix+'_circuit')
    level = b.selectbox('Filtrar nível', ['Todos']+LEVELS, key=prefix+'_level')
    st.button('Abrir Resumo de bobinas', on_click=open_summary)
    if st.session_state.pop('subpark_saved', False):
        st.success('Trecho salvo. O Resumo de bobinas já considera os lançamentos deste subparque.')
    groups, _, _ = phase_groups(project, park)
    a, b = st.columns(2)
    a.metric('Trechos por circuito e nível', len(groups))
    b.metric('Bobinas identificadas', len({r.get('bobina') for group in groups for r in group if r.get('bobina')}))
    for installation, title in [('AÉREO', 'Rede aérea'), ('SUBTERRÂNEO', 'Rede subterrânea')]:
        st.subheader(title)
        visible, warnings, current = phase_groups(project, park,
            None if circuit == 'Todos' else circuit, None if level == 'Todos' else level, installation)
        if visible:
            html=table_html(visible,underground=True) if installation=='SUBTERRÂNEO' else aerial_table_html(project,visible)
            st.markdown(html, unsafe_allow_html=True)
            if installation=='AÉREO':
                st.caption('Estrutura da aba RSA-01, sem as colunas L a S. Distância projeto exibe a necessidade do vão sem arredondar; diferenças entre níveis são identificadas na célula. Sobra bobina é o saldo na obra após os lançamentos de todos os subparques. O arredondamento continua sendo feito uma vez por lançamento contínuo.')
        else:
            st.info('Nenhum trecho nesta seção para os filtros selecionados.')
        if warnings:
            with st.expander(f'Pendências — {title} ({len(warnings)})'):
                for warning in warnings:
                    st.warning(warning)
        with st.expander(f'Adicionar ou editar trecho — {title}'):
            group_editor(project, park, installation, visible, prefix, circuit, level)
        selection(project,park,installation,visible,f'{prefix}_{park}_{installation}_{st.session_state.edit_version}')
    st.caption('A → B → C por trecho, com separador duplo. Reservas em metros incluem sobras de caixas, postes e saídas de turbina. O resumo soma a metragem sem arredondar cada linha e arredonda uma vez por lançamento contínuo.')
    render_optimization(project, park)


def group_editor(project, park, installation, groups, prefix, circuit_filter, level_filter):
    key = f"{prefix}_{park}_{installation}_{st.session_state.edit_version}"
    def label(index):
        if index == -1:
            return 'Novo trecho (A, B e C)'
        row = next(r for r in groups[index] if not r.get('ausente'))
        return f"{row['circuito']} · N{row['nivel']} · {row['de']} → {row['para']} · {row['rota']} · ordem {row['ordem']}"
    selected = st.selectbox('Trecho para editar', [-1]+list(range(len(groups))), format_func=label, key=key+'_group')
    originals = [] if selected == -1 else [r for r in groups[selected] if not r.get('ausente')]
    first = originals[0] if originals else {}
    form_key = key+f'_{selected}_{circuit_filter}_{level_filter}'
    with st.form(form_key):
        a, b, c = st.columns(3)
        circuit_options = [None]+CIRCUITS
        initial_circuit = first.get('circuito') or (circuit_filter if circuit_filter != 'Todos' else 'C01')
        circuit = a.selectbox('Circuito do trecho', circuit_options,
            index=circuit_options.index(initial_circuit) if initial_circuit in circuit_options else 0,
            format_func=lambda v:v or 'Selecione o circuito')
        initial_level = str(first.get('nivel', level_filter if level_filter != 'Todos' else '1'))
        level = b.selectbox('Nível do trecho', LEVELS, index=LEVELS.index(initial_level) if initial_level in LEVELS else 0)
        order = c.number_input('Ordem na rota', min_value=1.0, value=max(1.0, float(first.get('ordem', 1))), step=1.0)
        a, b, c = st.columns(3)
        start = a.text_input('De', first.get('de', ''))
        end = b.text_input('Para', first.get('para', ''))
        route = c.text_input('Rota', first.get('rota', 'Principal'))
        cuts = ['PERMITIDO', 'PROIBIDO', 'OBRIGATORIO']
        cut = st.selectbox('Corte no fim do trecho', cuts, index=cuts.index(first.get('corte_fim', 'PERMITIDO')))
        fields = ['fase', 'condutor', 'bobina_original', 'linear', 'folga', 'reserva', 'observacao']
        if installation == 'SUBTERRÂNEO':
            fields = ['fase', 'condutor', 'bobina_original', 'linear', 'folga'] + RESERVE_FIELDS + ['observacao']
        rows = []
        for phase in ('A', 'B', 'C'):
            source = next((r for r in originals if r['fase'] == phase), {})
            rows.append(dict(fase=phase, condutor=source.get('condutor', ''),
                bobina_original=source.get('bobina', ''), linear=source.get('linear', 0.0),
                folga=source.get('folga', .02 if installation == 'SUBTERRÂNEO' else .05),
                reserva=source.get('reserva', 0.0), observacao=source.get('observacao', '')))
            if installation == 'SUBTERRÂNEO':
                rows[-1].update({f:source.get(f, 0.0) for f in RESERVE_FIELDS})
                if not any(f in source for f in RESERVE_FIELDS):
                    rows[-1]['reserva_outros'] = source.get('reserva', 0.0)
        reel_options = sorted({r['id'] for r in project['bobinas'] if r.get('tipo') == installation} |
                              {r['bobina_original'] for r in rows if r['bobina_original']}, key=natural)
        edited = st.data_editor(pd.DataFrame(rows, columns=fields), hide_index=True, width='stretch',
            disabled=['fase'], num_rows='fixed', key=form_key+'_phases', column_config={
                'fase':st.column_config.TextColumn('Fase'),
                'condutor':st.column_config.SelectboxColumn('Condutor',options=conductor_options(project,installation),required=True),
                'bobina_original':st.column_config.SelectboxColumn('Bobina', options=['']+reel_options),
                'linear':st.column_config.NumberColumn('Linear [m]', min_value=0.01, required=True),
                'folga':st.column_config.NumberColumn('Folga (0,05 = 5%)', min_value=0.0, max_value=1.0, required=True),
                'reserva':st.column_config.NumberColumn('Reservas totais [m]', min_value=0.0, required=True),
                'qte_caixas':st.column_config.NumberColumn('Qte. caixas', min_value=0.0, step=1.0, required=True),
                'qte_postes':st.column_config.NumberColumn('Qte. postes', min_value=0.0, step=1.0, required=True),
                'qte_turbinas':st.column_config.NumberColumn('Qte. turbinas', min_value=0.0, step=1.0, required=True),
                'sobra_caixa':st.column_config.NumberColumn('Sobra total caixas [m]', min_value=0.0, required=True),
                'sobra_poste':st.column_config.NumberColumn('Sobra total postes [m]', min_value=0.0, required=True),
                'sobra_turbina':st.column_config.NumberColumn('Sobra total saída turbina [m]', min_value=0.0, required=True),
                'reserva_outros':st.column_config.NumberColumn('Outras reservas / legado [m]', min_value=0.0, required=True),
                'observacao':st.column_config.TextColumn('Observações')})
        st.caption('O circuito, nível, De e Para valem para as três fases. Informe o condutor e a bobina de cada fase. Reservas totais = sobra de caixas + postes + saída de turbina, em metros.')
        if installation == 'SUBTERRÂNEO':
            st.caption('As sobras são totais em metros, como no controle; não são multiplicadas novamente pelas quantidades. Reservas de projetos antigos, sem detalhamento, ficam em Outras reservas / legado.')
        if st.form_submit_button('Salvar trecho e atualizar resumo', type='primary'):
            try:
                candidate = replace_group(project, park, installation, [r['id'] for r in originals],
                    dict(circuito=circuit, nivel=level, ordem=order, de=start, para=end, rota=route, corte_fim=cut),
                    json.loads(edited.to_json(orient='records', force_ascii=False)))
                projects.save(candidate)
            except (ValueError, OSError, sqlite3.Error) as exc:
                st.error(str(exc))
            else:
                project.clear()
                project.update(candidate)
                st.session_state.edit_version += 1
                st.session_state.subpark_saved = True
                st.rerun()
