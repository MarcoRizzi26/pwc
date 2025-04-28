import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

# Configurações da página
st.set_page_config(page_title="Consolidador de Fundos", page_icon="📈", layout="wide")

st.title("📈 Consolidador de Fundos")
st.write("Faça upload dos arquivos necessários para consolidar os dados de resgates e aplicações.")

# Upload dos arquivos
nome_fundos_file = st.file_uploader("Upload do arquivo NOME-FUNDOS.xlsx", type="xlsx")
auc_file = st.file_uploader("Upload do arquivo AUC do dia (.xlsx, qualquer nome)", type="xlsx")

resgates_files = st.file_uploader("Upload dos arquivos de RESGATES (.xlsx)", type="xlsx", accept_multiple_files=True)
aplicacoes_files = st.file_uploader("Upload dos arquivos de APLICAÇÕES (.xlsx)", type="xlsx", accept_multiple_files=True)

# Função para consolidar múltiplos arquivos
def consolidar_arquivos(arquivos, fundos_df):
    dfs = []
    for file in arquivos:
        df = pd.read_excel(file)

        if 'cnpj do fundo' not in df.columns:
            continue  # pula arquivos errados

        df.rename(columns={'cnpj do fundo': 'CNPJ'}, inplace=True)
        df = df.merge(fundos_df, on='CNPJ', how='left')
        dfs.append(df)

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        return pd.DataFrame()

# Função para converter DataFrame em arquivo Excel
def converter_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# Processamento principal
if nome_fundos_file and auc_file and resgates_files and aplicacoes_files:
    fundos_df = pd.read_excel(nome_fundos_file)
    auc = pd.read_excel(auc_file)

    resgates = consolidar_arquivos(resgates_files, fundos_df)
    aplicacoes = consolidar_arquivos(aplicacoes_files, fundos_df)

    # Tratamento de resgates
    resgates.rename(columns={'número da conta': 'Código da Conta', 'Nome do Fundo': 'Instrumento (Nome)'}, inplace=True)

    # RESGATES - tipo RT
    resgates_rt = resgates[resgates["tipo de resgate"] == "RT"]
    merged_df = resgates_rt.merge(auc, on=["Código da Conta", "Instrumento (Nome)"], how="left")
    merged_df = merged_df.groupby(['Código da Conta', 'Instrumento (Nome)'], as_index=False)['Valor Bruto'].sum()
    df_cleaned = merged_df.drop_duplicates(subset=['Código da Conta', 'Instrumento (Nome)'])

    colunas_remover = [
        "CNPJ", "CPF/CNPJ", "Nome da Conta", "Subclasse do Ativo", "Quantidade", "Preço",
        "Data de Alocação Inicial", "Categoria do Instrumento", "Data de Referência",
        "Classe do Ativo", "Valor Líquido", "Taxa", "Nome Emissor", "Instrumento (Símbolo)",
        "InvestorType", "valor do resgate"
    ]
    df_cleaned = df_cleaned.drop(columns=colunas_remover, errors='ignore')
    df_cleaned.rename(columns={'Valor Bruto': 'valor do resgate'}, inplace=True)
    df_cleaned['tipo de resgate'] = 'RT'

    # RESGATES - tipo RP
    resgates_rp = resgates[resgates["tipo de resgate"] == "RP"]

    # Junta RT e RP
    resgates_fim = pd.concat([df_cleaned, resgates_rp], ignore_index=True).reset_index(drop=True)
    resgates_fim = resgates_fim.drop(columns=["CNPJ"], errors='ignore')

    # Consolidação final
    resgates_por_fundo = resgates_fim.groupby('Instrumento (Nome)')['valor do resgate'].sum().reset_index()
    aplicacoes_por_fundo = aplicacoes.groupby('Nome do Fundo')['valor da aplicacao'].sum().reset_index()

    # Gráfico
    st.subheader("📊 Gráfico Comparativo de Resgates e Aplicações")
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(resgates_por_fundo['Instrumento (Nome)'], resgates_por_fundo['valor do resgate'],
           label='Resgates', width=0.4, align='center', color='red')
    ax.bar(aplicacoes_por_fundo['Nome do Fundo'], aplicacoes_por_fundo['valor da aplicacao'],
           label='Aplicações', width=0.4, align='edge', color='green')
    ax.set_xlabel('Nome do Fundo')
    ax.set_ylabel('Valor (R$)')
    ax.set_title('Comparação entre Resgates e Aplicações por Fundo')
    ax.legend()
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    st.pyplot(fig)

    # Formatar valores monetários
    resgates_por_fundo['valor do resgate'] = resgates_por_fundo['valor do resgate'].apply(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    aplicacoes_por_fundo['valor da aplicacao'] = aplicacoes_por_fundo['valor da aplicacao'].apply(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # Mostrar tabelas
    st.subheader("📄 Resgates por Fundo")
    st.dataframe(resgates_por_fundo)

    st.subheader("📄 Aplicações por Fundo")
    st.dataframe(aplicacoes_por_fundo)

else:
    st.warning("⚠️ Faça upload de todos os arquivos para prosseguir.")
