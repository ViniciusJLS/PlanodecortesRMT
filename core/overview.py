"""Indicadores por subparque derivados do mesmo resumo de bobinas da obra."""
from collections import Counter, defaultdict
from decimal import Decimal
from .inventory import summarize, park_id, amount


def chart_data(project):
    rows, parks, current = summarize(project)
    parks = sorted(set(parks) | {park_id(p) for p in project.get('subparques', [])})
    duplicates = {k for k, n in Counter(r['Bobina'] for r in rows).items() if n > 1}
    details, pending = [], 0
    unassigned = Decimal(0)
    for row in rows:
        if row['Bobina'] in duplicates:
            pending += 1
            continue
        adjustment = amount(row['Ajuste / sem parque [m]'])
        if adjustment is not None:
            unassigned += adjustment
        for park in parks:
            value = amount(row.get(park, 0))
            if value is None or value < 0:
                pending += 1
            elif value > 0:
                details.append({'Subparque': park, 'Bobina': row['Bobina'],
                    'Condutor': row['Condutor'] or 'Não informado', 'Comprimento [m]': float(value)})
    totals = defaultdict(lambda: {'ids': set(), 'length': Decimal(0)})
    for row in details:
        group = totals[row['Condutor']]
        group['ids'].add(row['Bobina'])
        group['length'] += Decimal(str(row['Comprimento [m]']))
    conductors = [{'Condutor': name, 'Bobinas utilizadas': len(v['ids']),
                   'Comprimento [m]': float(v['length'])} for name, v in sorted(totals.items())]
    return dict(details=details, conductors=conductors, parks=parks, current=current,
                pending=pending, unassigned=float(unassigned))


def pie(frame, category, value):
    import altair as alt
    # Vega interprets brackets/dots in field names as nested data access.
    # Stable internal fields keep the original labels only as display titles.
    data = frame[[category, value]].copy()
    data.columns = ['category', 'value']
    return (alt.Chart(data).transform_joinaggregate(total='sum(value)')
        .transform_calculate(percent='datum.value / datum.total')
        .mark_arc(innerRadius=45, outerRadius=110).encode(
            theta=alt.Theta('value:Q', title=value, stack=True),
            color=alt.Color('category:N', title=category, legend=alt.Legend(title=category)),
            tooltip=[alt.Tooltip('category:N', title=category),
                     alt.Tooltip('value:Q', title=value, format=',.2f' if '[m]' in value else ',.0f'),
                     alt.Tooltip('percent:Q', title='Participação', format='.1%')]
        ).properties(height=290))



def render(project):
    import pandas as pd
    import streamlit as st
    data = chart_data(project)
    st.subheader('Utilização de bobinas nos subparques')
    st.caption('Metragem por bobina, somando fases e níveis. Fonte: o mesmo cálculo da página Resumo de bobinas; plano atual quando disponível, ou lançamentos e histórico importado.')
    if not data['current']:
        st.info('Gráficos baseados nos lançamentos cadastrados e no histórico importado. Gere um plano atualizado para visualizar a nova alocação.')
    if data['pending']:
        st.warning('Há valores pendentes, negativos ou identificações de bobina duplicadas. Os registros afetados não entram nos gráficos; confira o Resumo de bobinas.')
    if data['unassigned']:
        st.caption(f"Ajustes / consumo sem subparque: {data['unassigned']:,.2f} m. Não incluídos nos gráficos dos parques.")
    if not data['details']:
        st.info('Ainda não há utilização positiva de bobinas vinculada aos subparques desta obra.')
        return
    totals = pd.DataFrame(data['conductors'])
    st.markdown('**Total da obra por condutor**')
    left, right = st.columns(2)
    with left:
        st.markdown('Quantidade de bobinas utilizadas')
        st.altair_chart(pie(totals, 'Condutor', 'Bobinas utilizadas'), width='stretch')
    with right:
        st.markdown('Comprimento utilizado nos parques [m]')
        st.altair_chart(pie(totals, 'Condutor', 'Comprimento [m]'), width='stretch')
    st.caption('A bobina compartilhada aparece em cada parque atendido, mas é contada uma única vez no total por condutor. O comprimento representa o cabo utilizado nos parques, não o comprimento nominal das bobinas nem a extensão geográfica da rede.')
    st.dataframe(totals, hide_index=True, width='stretch')
    selected = st.multiselect('Subparques exibidos', data['parks'], default=data['parks'],
                              key='overview_parks_' + project['id'])
    frame = pd.DataFrame(data['details'])
    for index in range(0, len(selected), 2):
        columns = st.columns(2)
        for column, park in zip(columns, selected[index:index+2]):
            with column:
                subset = frame[frame['Subparque'] == park]
                st.markdown(f'**{park}**')
                if subset.empty:
                    st.info('Sem utilização de bobinas registrada.')
                    continue
                st.caption(f"{subset['Bobina'].nunique()} bobinas · {subset['Comprimento [m]'].sum():,.2f} m")
                st.altair_chart(pie(subset, 'Bobina', 'Comprimento [m]'), width='stretch')
                with st.expander('Ver bobinas e metragens de ' + park):
                    st.dataframe(subset.drop(columns='Subparque'), hide_index=True, width='stretch')
