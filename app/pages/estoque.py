import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from datetime import datetime

def upload_files():
    auc_file = st.file_uploader("Upload do arquivo AUC", type=["xlsx"])
    status_file = st.file_uploader("Upload do arquivo Status", type=["xlsx"])
    baseclientes_file = st.file_uploader("Upload do arquivo Base de Clientes", type=["xlsx"])
    estoque_file = st.file_uploader("Upload do arquivo Estoque Consolidado", type=["xlsx"])
    
    return auc_file, status_file, baseclientes_file, estoque_file

def process_analysis(auc_file, status_file, baseclientes_file, estoque_file):
    auc = pd.read_excel(auc_file)
    status = pd.read_excel(status_file)
    baseclientes = pd.read_excel(baseclientes_file)
    estoque = pd.read_excel(estoque_file)

    auc["PL"] = auc.groupby("Código da Conta")["Valor Bruto"].transform("sum")
    status = status.rename(columns={"Código Ativo": "Instrumento (Símbolo)"})

    df_padronizado = auc.merge(status[['Instrumento (Símbolo)', 'RISCO', '% Sugerida']],
                               on="Instrumento (Símbolo)", how="left")

    colunas_remover = [
        "CPF/CNPJ", "Subclasse do Ativo", "Data de Alocação Inicial",
        "Categoria do Instrumento", "Data de Referência", "Classe do Ativo", "Taxa",
        "Nome Emissor", "InvestorType"
    ]
    df_padronizado.drop(columns=colunas_remover, errors='ignore', inplace=True)
    df_padronizado.dropna(subset=['RISCO'], inplace=True)

    df_filtrado = df_padronizado[df_padronizado["Código da Conta"].isin(baseclientes["COD"])]
    df_filtrado.to_excel("dados_filtrados.xlsx", index=False)

    nw_auc = df_padronizado[df_padronizado["Código da Conta"].isin(baseclientes["COD"])]
    nw_auc.to_excel("new_auc.xlsx", index=False)

    nw_auc["Exposição"] = nw_auc.groupby(["Código da Conta", "RISCO"])["Valor Bruto"].transform("sum")
    nw_auc["Valor-Permitido"] = nw_auc["% Sugerida"] * nw_auc["PL"]

    colunas_remover = ["Nome da Conta", "Instrumento (Nome)", "Valor Líquido"]
    nw_auc.drop(columns=colunas_remover, errors='ignore', inplace=True)

    df_filtrado = nw_auc.drop_duplicates(subset=["Código da Conta", "RISCO"])
    df_filtrado["valor-remanescente"] = df_filtrado["Exposição"] - df_filtrado["Valor-Permitido"]

    vendedores = df_filtrado[df_filtrado["valor-remanescente"] > 0].reset_index(drop=True)

    df_riscos_liquidar = (
        vendedores.groupby("RISCO", as_index=False)["valor-remanescente"]
        .sum()
        .sort_values(by="valor-remanescente", ascending=False)
        .reset_index(drop=True)
    )

    data_coluna = datetime.today().strftime('%Y-%m-%d')
    df_riscos_liquidar.rename(columns={"valor-remanescente": data_coluna}, inplace=True)

    st.subheader("Tabela de Riscos a Liquidar")
    st.write(df_riscos_liquidar)

    df_merged = pd.merge(estoque, df_riscos_liquidar, on="RISCO", how="outer")

    colunas_data = [col for col in df_merged.columns if col != 'RISCO']
    colunas_data_ordenadas = sorted(colunas_data, key=lambda x: pd.to_datetime(str(x)))
    df_merged = df_merged[['RISCO'] + colunas_data_ordenadas]

    df = pd.DataFrame(df_merged)
    df.set_index("RISCO", inplace=True)
    df.replace("-", np.nan, inplace=True)
    df = df.astype(float)
    df = df.transpose()
    df.index = pd.to_datetime(df.index)

    ultimos_riscos = df.iloc[-1].sort_values(ascending=False).head(10).index
    df = df[ultimos_riscos]

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

    st.subheader("Gráfico de Evolução dos Riscos")
    st.pyplot(plt)

def main():
    st.title("Estoque de Carteira dos Clientes")

    st.write("O xlsx do 'status' deve conter as seguintes colunas:")
    st.write("| Código Ativo | NOME | RISCO | PU | % Sugerida |")

    st.write("O xlsx de 'clientes' deve conter APENAS a seguinte coluna:")
    st.write("| COD |")
    
    auc_file, status_file, baseclientes_file, estoque_file = upload_files()
    
    if auc_file and status_file and baseclientes_file and estoque_file:
        process_analysis(auc_file, status_file, baseclientes_file, estoque_file)

if __name__ == "__main__":
    main()
