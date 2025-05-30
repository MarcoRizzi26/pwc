import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(layout="wide", page_title="Relatório de Fundos")
st.title("📊 Relatório de Aplicações e Resgates por Fundo")

# ========== Funções Auxiliares ==========

def padronizar_cnpj(cnpj):
    return str(cnpj).replace(',', '').strip().zfill(14)

def carregar_dados(nome_fundos_file, auc_file, aplicacoes_files, resgates_files):
    nome_fundos = pd.read_excel(nome_fundos_file)
    auc = pd.read_excel(auc_file)
    aplicacoes = pd.concat([pd.read_excel(f) for f in aplicacoes_files], ignore_index=True)
    resgates = pd.concat([pd.read_excel(f) for f in resgates_files], ignore_index=True)
    return nome_fundos, auc, aplicacoes, resgates

def tratar_resgates_rt(resgates, auc):
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

    return pd.concat([resgates_rt_final, resgates_others], ignore_index=True)

def aplicar_padronizacao_e_merge(aplicacoes, resgates, nome_fundos):
    aplicacoes['cnpj do fundo'] = aplicacoes['cnpj do fundo'].apply(padronizar_cnpj)
    resgates['cnpj do fundo'] = resgates['cnpj do fundo'].apply(padronizar_cnpj)
    nome_fundos['CNPJ'] = nome_fundos['CNPJ'].apply(padronizar_cnpj)

    nome_fundos = nome_fundos.drop_duplicates(subset='CNPJ')

    aplicacoes_com_nome = aplicacoes.merge(
        nome_fundos[['CNPJ', 'Nome do Fundo']],
        left_on='cnpj do fundo',
        right_on='CNPJ',
        how='left'
    )

    resgates_com_nome = resgates.merge(
        nome_fundos[['CNPJ', 'Nome do Fundo']],
        left_on='cnpj do fundo',
        right_on='CNPJ',
        how='left'
    )

    return aplicacoes_com_nome, resgates_com_nome

def gerar_relatorio(aplicacoes, resgates):
    aplicacoes_por_fundo = aplicacoes.groupby('Nome do Fundo')['valor da aplicacao'].sum().reset_index()
    resgates_por_fundo = resgates.groupby('Nome do Fundo')['valor do resgate'].sum().reset_index()

    relatorio = pd.merge(aplicacoes_por_fundo, resgates_por_fundo, on='Nome do Fundo', how='outer').fillna(0)

    relatorio['valor da aplicacao (R$)'] = relatorio['valor da aplicacao'].apply(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    relatorio['valor do resgate (R$)'] = relatorio['valor do resgate'].apply(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    return relatorio

def exibir_resultados(relatorio):
    st.success("✅ Relatório consolidado com sucesso!")

    st.subheader("📄 Tabela Consolidada")
    st.dataframe(relatorio[['Nome do Fundo', 'valor da aplicacao (R$)', 'valor do resgate (R$)']])

    st.subheader("📈 Gráfico Comparativo")
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(relatorio['Nome do Fundo'], relatorio['valor da aplicacao'], label='Aplicações', color='green')
    ax.bar(relatorio['Nome do Fundo'], relatorio['valor do resgate'], label='Resgates', color='red', alpha=0.7)
    ax.set_title('Aplicações vs Resgates por Fundo')
    ax.set_ylabel('Valor (R$)')
    ax.legend()
    plt.xticks(rotation=45, ha='right')
    st.pyplot(fig)

# ========== Uploads ==========
st.header("📁 Upload de Arquivos")
col1, col2 = st.columns(2)

with col1:
    nome_fundos_file = st.file_uploader("Upload do arquivo 'NOME-FUNDOS.xlsx'", type='xlsx')
with col2:
    auc_file = st.file_uploader("Upload do arquivo 'AUC - xx.xx.xxxx.xlsx'", type='xlsx')

aplicacoes_files = st.file_uploader("Upload de arquivos de aplicações (.xlsx)", type="xlsx", accept_multiple_files=True)
resgates_files = st.file_uploader("Upload de arquivos de resgates (.xlsx)", type="xlsx", accept_multiple_files=True)

# ========== Execução principal ==========
if nome_fundos_file and auc_file and aplicacoes_files and resgates_files:
    nome_fundos, auc, aplicacoes, resgates = carregar_dados(
        nome_fundos_file, auc_file, aplicacoes_files, resgates_files
    )

    resgates_final = tratar_resgates_rt(resgates, auc)
    aplicacoes_com_nome, resgates_com_nome = aplicar_padronizacao_e_merge(
        aplicacoes, resgates_final, nome_fundos
    )

    relatorio = gerar_relatorio(aplicacoes_com_nome, resgates_com_nome)
    exibir_resultados(relatorio)
else:
    st.info("📥 Faça upload de todos os arquivos para gerar o relatório.")
