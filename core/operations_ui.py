"""Configuração e prestação de contas dos critérios operacionais por obra."""
from copy import deepcopy
import pandas as pd
import streamlit as st
from .operations import settings, parameter_errors, report, PROXIMITY, VERSION


def render_criteria(project, commit):
    p=settings(project)
    parks=sorted(set(project.get('subparques',[])) | {r['parque'] for r in project['trechos']})
    st.subheader('Prioridades de lançamento')
    st.markdown('1. Reduzir o número de lançamentos contínuos por fase.\n2. Preferir bobinas consumidas em um único lançamento, com sobra tolerada.\n3. Evitar sobras intermediárias e lançamentos curtos.\n4. Preferir compartilhamento entre parques próximos.\n5. Desempatar pela metragem de estoque mobilizada.')
    st.caption('Cada prioridade preserva o resultado obtido nas anteriores. Os indicadores representam operações de equipe; não calculam custo em reais. Restrições de corte e capacidade continuam obrigatórias.')
    with st.form('criteria'):
        low=st.number_input('Sobra tolerada até [m]',min_value=0.,max_value=1000000.,value=float(p['sobra_tolerada']))
        high=st.number_input('Sobra reutilizável acima de [m]',min_value=0.,max_value=1000000.,value=float(p['sobra_reutilizavel']))
        short=st.number_input('Evitar lançamentos de até [m]',min_value=0.,max_value=1000000.,value=float(p['lancamento_minimo']))
        st.caption('Padrão: até 60 m é tolerado; mais de 60 até 500 m é uma sobra a evitar; acima de 500 m é reutilizável. São preferências: uma exceção pode ser necessária para concluir a rede.')
        st.markdown('**Proximidade física entre subparques**')
        st.caption('Cadastre cada par uma única vez. A numeração dos parques não indica distância. Pares ausentes ficam como Não informada.')
        pairs=st.data_editor(pd.DataFrame(p['proximidades'],columns=['parque_a','parque_b','proximidade']),
            num_rows='dynamic',hide_index=True,key='operational_pairs_'+project['id'],
            column_config={'parque_a':st.column_config.SelectboxColumn('Parque A',options=parks,required=True),
                'parque_b':st.column_config.SelectboxColumn('Parque B',options=parks,required=True),
                'proximidade':st.column_config.SelectboxColumn('Proximidade',options=list(PROXIMITY),required=True)})
        order=st.text_area('Ordem de execução: um subparque por linha',value='\n'.join(p['ordem_execucao']),
            help='Use os nomes exatos dos subparques. Quando todos estiverem informados, o transporte considera somente a sequência de parques atendidos por cada bobina.')
        st.caption('Sem ordem completa, o transporte é avaliado pelos pares que compartilham bobinas, sem estimar uma rota física.')
        if st.form_submit_button('Salvar critérios'):
            candidate=deepcopy(project)
            records=pairs.where(pd.notna(pairs),None).to_dict('records')
            records=[{k:str(v).strip() if v is not None else '' for k,v in r.items()} for r in records if any(r.values())]
            candidate['criterios'].update(versao_operacional=VERSION,sobra_tolerada=low,sobra_reutilizavel=high,
                lancamento_minimo=short,proximidades=records,ordem_execucao=[v.strip() for v in order.splitlines() if v.strip()])
            errors=parameter_errors(candidate)
            unknown=set(candidate['criterios']['ordem_execucao'])-set(parks)
            if unknown:errors.append('Ordem de execução: cadastre primeiro os subparques: '+', '.join(sorted(unknown)))
            if errors:
                for error in errors:st.error(error)
            else:
                project['criterios']=candidate['criterios']
                commit()
                st.success('Critérios salvos para esta obra. Gere o plano novamente para aplicá-los.')


def render_report(project,cuts):
    r=report(project,cuts)
    with st.expander('Análise operacional da obra: sobras e transporte'):
        a,b,c=st.columns(3)
        a.metric('Bobinas em lançamento único',r['bobinas_lancamento_completo'])
        b.metric('Sobras intermediárias',r['sobras_intermediarias'])
        c.metric('Lançamentos curtos',len(r['lancamentos_curtos']))
        st.caption('Lançamento único: consumo em uma operação por fase, terminando com saldo dentro da tolerância. As exceções abaixo não invalidam um plano fisicamente viável.')
        if r['bobinas']:st.dataframe(pd.DataFrame(r['bobinas']),hide_index=True)
        if r['lancamentos_curtos']:
            st.markdown('**Operações curtas para avaliação da equipe**')
            st.dataframe(pd.DataFrame(r['lancamentos_curtos']),hide_index=True)
        st.caption('Transporte pela ordem de execução informada.' if r['transporte_por_ordem'] else 'Compartilhamento avaliado por pares; ordem de execução incompleta ou não informada.')
        if r['transportes']:st.dataframe(pd.DataFrame(r['transportes']),hide_index=True)
        else:st.write('Nenhuma bobina compartilhada entre subparques neste plano.')
