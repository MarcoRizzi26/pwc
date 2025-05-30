import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(layout="wide", page_title="Relatório de Fundos")

st.title("📊 Relatório de Aplicações e Resgates por Fundo")

# Upload de arquivos
st.header("📁 Upload de Arquivos")
col1, col2 = st.columns(2)

with col1:
    nome_fundos_file = st.file_uploader("Upload do arquivo 'NOME-FUNDOS.xlsx'", type='xlsx')

with col2:
    auc_file = st.file_uploader("Upload do arquivo 'AUC - xx.xx.xxxx.xlsx'", type='xlsx')

aplicacoes_files = st.file_uploader("Upload de arquivos de aplicações (.xlsx)", type="xlsx", accept_multiple_files=True)
resgates_files = st.file_uploader("Upload de arquivos de resgates (.xlsx)", type="xlsx", accept_multiple_files=True)

def padronizar_cnpj(cnpj):
    return str(cnpj).replace(',', '').strip().zfill(14)

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

if nome_fundos_file and auc_file and aplicacoes_files and resgates_files:
    # Leitura de arquivos
    nome_fundos = pd.read_excel(nome_fundos_file)
    auc = pd.read_excel(auc_file)
    aplicacoes = pd.concat([pd.read_excel(f) for f in aplicacoes_files], ignore_index=True)
    resgates = pd.concat([pd.read_excel(f) for f in resgates_files], ignore_index=True)

    # Separar RT dos outros tipos
    resgates_rt = resgates[resgates['tipo de resgate'] == 'RT'].copy()
    resgates_others = resgates[resgates['tipo de resgate'] != 'RT'].copy()

    # Padronizar strings
    resgates_rt['cnpj do fundo'] = resgates_rt['cnpj do fundo'].astype(str).str.replace(',', '').str.strip()
    resgates_rt['número da conta'] = resgates_rt['número da conta'].astype(str).str.strip()
    auc['Instrumento (Símbolo)'] = auc['Instrumento (Símbolo)'].astype(str).str.strip()
    auc['Código da Conta'] = auc['Código da Conta'].astype(str).str.strip()

    # Merge RT com AUC
    auc_reduzido = auc[['Código da Conta', 'Instrumento (Símbolo)', 'Valor Bruto']].copy()
    resgates_rt_merged = resgates_rt.merge(
        auc_reduzido,
        left_on=['número da conta', 'cnpj do fundo'],
        right_on=['Código da Conta', 'Instrumento (Símbolo)'],
        how='left'
    )
    resgates_rt_merged['valor do resgate'] = resgates_rt_merged['Valor Bruto']
    resgates_rt_final = resgates_rt_merged[['número da conta', 'cnpj do fundo', 'valor do resgate', 'tipo de resgate']]
    resgates_others = resgates_others[['número da conta', 'cnpj do fundo', 'valor do resgate', 'tipo de resgate']]
    resgates_final = pd.concat([resgates_rt_final, resgates_others], ignore_index=True)

    # Padronização de CNPJs
    aplicacoes['cnpj do fundo'] = aplicacoes['cnpj do fundo'].apply(padronizar_cnpj)
    resgates_final['cnpj do fundo'] = resgates_final['cnpj do fundo'].apply(padronizar_cnpj)
    nome_fundos['CNPJ'] = nome_fundos['CNPJ'].apply(padronizar_cnpj)
    nome_fundos = nome_fundos.drop_duplicates(subset='CNPJ')

    # Merge com nome do fundo
    aplicacoes_com_nome = aplicacoes.merge(nome_fundos[['CNPJ', 'Nome do Fundo']],
                                           left_on='cnpj do fundo', right_on='CNPJ', how='left')
    resgates_com_nome = resgates_final.merge(nome_fundos[['CNPJ', 'Nome do Fundo']],
                                             left_on='cnpj do fundo', right_on='CNPJ', how='left')

    # Agrupamento por fundo
    aplicacoes_por_fundo = aplicacoes_com_nome.groupby('Nome do Fundo')['valor da aplicacao'].sum().reset_index()
    resgates_por_fundo = resgates_com_nome.groupby('Nome do Fundo')['valor do resgate'].sum().reset_index()
    relatorio = pd.merge(aplicacoes_por_fundo, resgates_por_fundo, on='Nome do Fundo', how='outer').fillna(0)

    # Cálculo do NNM
    relatorio['NNM'] = relatorio['valor da aplicacao'] - relatorio['valor do resgate']

    # Formatar colunas monetárias
    relatorio['valor da aplicacao (R$)'] = relatorio['valor da aplicacao'].apply(formatar_moeda)
    relatorio['valor do resgate (R$)'] = relatorio['valor do resgate'].apply(formatar_moeda)
    relatorio['NNM (R$)'] = relatorio['NNM'].apply(formatar_moeda)

    st.success("✅ Relatório consolidado com sucesso!")

    # Exibir tabela
    st.subheader("📄 Tabela Consolidada")
    st.dataframe(relatorio[['Nome do Fundo', 'valor da aplicacao (R$)', 'valor do resgate (R$)', 'NNM (R$)']])

    # Gráfico com valores
    st.subheader("📈 Gráfico Comparativo")
    fig, ax = plt.subplots(figsize=(12, 6))

    x = relatorio['Nome do Fundo']
    y_ap = relatorio['valor da aplicacao']
    y_rg = relatorio['valor do resgate']

    largura = 0.4
    indices = range(len(x))

    barras_ap = ax.bar([i - largura / 2 for i in indices], y_ap, width=largura, label='Aplicações', color='green')
    barras_rg = ax.bar([i + largura / 2 for i in indices], y_rg, width=largura, label='Resgates', color='red', alpha=0.7)

    # Adicionar valores somente na barra com valor maior (por par)
    for i, (valor_ap, valor_rg) in enumerate(zip(y_ap, y_rg)):
        if valor_ap >= valor_rg:
            valor = valor_ap
            pos_x = barras_ap[i].get_x() + barras_ap[i].get_width() / 2
        else:
            valor = valor_rg
            pos_x = barras_rg[i].get_x() + barras_rg[i].get_width() / 2

        ax.annotate(
            f"R$ {valor:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."),
            xy=(pos_x, valor),
            xytext=(0, 8),
            textcoords="offset points",
            ha='center', va='bottom', fontsize=9, fontweight='bold', color='black'
        )

    ax.set_title('Aplicações vs Resgates por Fundo')
    ax.set_ylabel('Valor (R$)')
    ax.set_xticks(indices)
    ax.set_xticklabels(x, rotation=45, ha='right')
    ax.legend()
    ax.set_ylim(top=max(y_ap.max(), y_rg.max()) * 1.2)

    st.pyplot(fig)

else:
    st.info("📥 Faça upload de todos os arquivos para gerar o relatório. V2")
