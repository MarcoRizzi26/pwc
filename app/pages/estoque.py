import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from datetime import datetime

# Upload dos arquivos
def upload_files():
    auc_file = st.file_uploader("Upload do arquivo AUC", type=["xlsx"])
    status_file = st.file_uploader("Upload do arquivo Status", type=["xlsx"])
    baseclientes_file = st.file_uploader("Upload do arquivo Base de Clientes", type=["xlsx"])
    estoque_file = st.file_uploader("Upload do arquivo Estoque Consolidado", type=["xlsx"])
    
    return auc_file, status_file, baseclientes_file, estoque_file

# Função principal de processamento
def process_analysis(auc_file, status_file, baseclientes_file, estoque_file):
    # Leitura dos arquivos
    auc = pd.read_excel(auc_file)
    status = pd.read_excel(status_file)
    baseclientes = pd.read_excel(baseclientes_file)
    estoque = pd.read_excel(estoque_file)

    # Calcular PL por conta
    auc["PL"] = auc.groupby("Código da Conta")["Valor Bruto"].transform("sum")
    status = status.rename(columns={"Código Ativo": "Instrumento (Símbolo)"})

    # Mesclar dados de risco
    df_padronizado = auc.merge(status[['Instrumento (Símbolo)', 'RISCO', '% Sugerida']],
                               on="Instrumento (Símbolo)", how="left")

    # Limpar colunas desnecessárias
    colunas_remover = [
        "CPF/CNPJ", "Subclasse do Ativo", "Data de Alocação Inicial",
        "Categoria do Instrumento", "Data de Referência", "Classe do Ativo", "Taxa",
        "Nome Emissor", "InvestorType"
    ]
    df_padronizado.drop(columns=colunas_remover, errors='ignore', inplace=True)
    df_padronizado.dropna(subset=['RISCO'], inplace=True)

    # Filtrar clientes da base
    df_filtrado = df_padronizado[df_padronizado["Código da Conta"].isin(baseclientes["COD"])]
    df_filtrado.to_excel("dados_filtrados.xlsx", index=False)

    # Reaproveitar para nova análise
    nw_auc = df_padronizado[df_padronizado["Código da Conta"].isin(baseclientes["COD"])]
    nw_auc.to_excel("new_auc.xlsx", index=False)

    nw_auc["Exposição"] = nw_auc.groupby(["Código da Conta", "RISCO"])["Valor Bruto"].transform("sum")
    nw_auc["Valor-Permitido"] = nw_auc["% Sugerida"] * nw_auc["PL"]

    # Remover colunas
    colunas_remover = ["Nome da Conta", "Instrumento (Nome)", "Valor Líquido"]
    nw_auc.drop(columns=colunas_remover, errors='ignore', inplace=True)

    df_filtrado = nw_auc.drop_duplicates(subset=["Código da Conta", "RISCO"])
    df_filtrado["valor-remanescente"] = df_filtrado["Exposição"] - df_filtrado["Valor-Permitido"]

    # Filtrar quem precisa vender
    vendedores = df_filtrado[df_filtrado["valor-remanescente"] > 0].reset_index(drop=True)

    df_riscos_liquidar = (
        vendedores.groupby("RISCO", as_index=False)["valor-remanescente"]
        .sum()
        .sort_values(by="valor-remanescente", ascending=False)
        .reset_index(drop=True)
    )

    # Renomear coluna para data atual
    data_coluna = datetime.today().strftime('%Y-%m-%d')
    df_riscos_liquidar.rename(columns={"valor-remanescente": data_coluna}, inplace=True)

    # Exibir tabela
    st.subheader("Tabela de Riscos a Liquidar")
    st.write(df_riscos_liquidar)

    # Juntar com estoque consolidado
    df_merged = pd.merge(estoque, df_riscos_liquidar, on="RISCO", how="outer")

    # Ordenar colunas por data
    colunas_data = [col for col in df_merged.columns if col != 'RISCO']
    colunas_data_ordenadas = sorted(colunas_data, key=lambda x: pd.to_datetime(str(x)))
    df_merged = df_merged[['RISCO'] + colunas_data_ordenadas]

    # Preparar dados para gráfico
    df = pd.DataFrame(df_merged)
    df.set_index("RISCO", inplace=True)
    df.replace("-", np.nan, inplace=True)
    df = df.astype(float)
    df = df.transpose()
    df.index = pd.to_datetime(df.index)

    # Filtrar top 10 riscos com maior valor mais recente
    ultimos_riscos = df.iloc[-1].sort_values(ascending=False).head(10).index
    df = df[ultimos_riscos]

    # Plotagem
    plt.figure(figsize=(12, 6))
    for risco in df.columns:
        plt.plot(df.index, df[risco], marker='o', label=risco)

    plt.xlabel("Data")
    plt.ylabel("Valor (R$)")
    plt.title("Top 10 Riscos - Evolução ao Longo do Tempo")
    plt.legend(loc="upper left", bbox_to_anchor=(1, 1))
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Exibir gráfico no Streamlit
    st.subheader("Gráfico de Evolução dos Riscos")
    st.pyplot(plt)

# Função principal da aplicação
def main():
    st.title("Análise de Carteira de Clientes")
    
    auc_file, status_file, baseclientes_file, estoque_file = upload_files()
    
    if auc_file and status_file and baseclientes_file and estoque_file:
        process_analysis(auc_file, status_file, baseclientes_file, estoque_file)

if __name__ == "__main__":
    main()
