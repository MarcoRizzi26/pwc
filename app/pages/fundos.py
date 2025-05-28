import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(layout="wide")

st.title("📊 Relatório Consolidado de Aplicações e Resgates")

# === Upload dos arquivos base ===
st.sidebar.header("📁 Upload dos Arquivos")

fundos_file = st.sidebar.file_uploader("Nome dos Fundos (NOME-FUNDOS.xlsx)", type="xlsx")
auc_file = st.sidebar.file_uploader("AUC (ex: AUC - 28.05.2025.xlsx)", type="xlsx")

aplicacoes_files = st.sidebar.file_uploader("Aplicações (vários arquivos .xlsx)", type="xlsx", accept_multiple_files=True)
resgates_files = st.sidebar.file_uploader("Resgates (vários arquivos .xlsx)", type="xlsx", accept_multiple_files=True)

if fundos_file and auc_file and aplicacoes_files and resgates_files:

    # === Leitura dos arquivos ===
    nome_fundos = pd.read_excel(fundos_file)
    auc = pd.read_excel(auc_file)

    def consolidar(arquivos):
        dfs = [pd.read_excel(f) for f in arquivos]
        return pd.concat(dfs, ignore_index=True)

    aplicacoes = consolidar(aplicacoes_files)
    resgates = consolidar(resgates_files)

    # === Processamento de RT ===
    resgates_rt = resgates[resgates['tipo de resgate'] == 'RT'].copy()
    resgates_others = resgates[resgates['tipo de resgate'] != 'RT'].copy()

    resgates_rt['cnpj do fundo'] = resgates_rt['cnpj do fundo'].astype(str).str.replace(',', '').str.strip()
    resgates_rt['número da conta'] = resgates_rt['número da conta'].astype(str).str.strip()
    auc['Instrumento (Símbolo)'] = auc['Instrumento (Símbolo)'].astype(str).str.strip()
    auc['Código da Conta'] = auc['Código da Conta'].astype(str).str.strip()

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

    # === Associar nome do fundo pelo CNPJ ===
    def padronizar_cnpj(cnpj):
        return str(cnpj).replace(',', '').strip().zfill(14)

    aplicacoes['cnpj do fundo'] = aplicacoes['cnpj do fundo'].apply(padronizar_cnpj)
    resgates_final['cnpj do fundo'] = resgates_final['cnpj do fundo'].apply(padronizar_cnpj)
    nome_fundos['CNPJ'] = nome_fundos['CNPJ'].apply(padronizar_cnpj)

    nome_fundos = nome_fundos.drop_duplicates(subset='CNPJ')

    aplicacoes_com_nome = aplicacoes.merge(
        nome_fundos[['CNPJ', 'Nome do Fundo']],
        left_on='cnpj do fundo',
        right_on='CNPJ',
        how='left'
    )

    resgates_com_nome = resgates_final.merge(
        nome_fundos[['CNPJ', 'Nome do Fundo']],
        left_on='cnpj do fundo',
        right_on='CNPJ',
        how='left'
    )

    # === Relatório ===
    aplicacoes_por_fundo = aplicacoes_com_nome.groupby('Nome do Fundo')['valor da aplicacao'].sum().reset_index()
    resgates_por_fundo = resgates_com_nome.groupby('Nome do Fundo')['valor do resgate'].sum().reset_index()

    relatorio = pd.merge(aplicacoes_por_fundo, resgates_por_fundo, on='Nome do Fundo', how='outer').fillna(0)

    relatorio['valor da aplicacao (R$)'] = relatorio['valor da aplicacao'].apply(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    relatorio['valor do resgate (R$)'] = relatorio['valor do resgate'].apply(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # === Exibir tabela ===
    st.subheader("📄 Relatório Consolidado por Fundo")
    st.dataframe(relatorio[['Nome do Fundo', 'valor da aplicacao (R$)', 'valor do resgate (R$)']])

    # === Gráfico ===
    st.subheader("📈 Gráfico Comparativo")
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(relatorio['Nome do Fundo'], relatorio['valor da aplicacao'], label='Aplicações', color='green')
    ax.bar(relatorio['Nome do Fundo'], relatorio['valor do resgate'], label='Resgates', color='red', alpha=0.7)
    ax.set_title('Aplicações vs Resgates por Fundo')
    ax.set_ylabel('Valor (R$)')
    plt.xticks(rotation=45, ha='right')
    ax.legend()
    st.pyplot(fig)

else:
    st.info("📂 Por favor, envie todos os arquivos necessários na barra lateral para gerar o relatório.")
