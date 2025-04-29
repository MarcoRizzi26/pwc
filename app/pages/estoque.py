import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

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
                               on="Instrumento (Símbolo)",
                               how="left")
    
    colunas_remover = [
        "CPF/CNPJ", "Subclasse do Ativo", "Data de Alocação Inicial",
        "Categoria do Instrumento", "Data de Referência", "Classe do Ativo", "Taxa",
        "Nome Emissor", "InvestorType"
    ]
    df_padronizado = df_padronizado.drop(columns=colunas_remover, errors='ignore')
    df_padronizado = df_padronizado.dropna(subset=['RISCO'])
    
    df_filtrado = df_padronizado[df_padronizado["Código da Conta"].isin(baseclientes["COD"])]
    
    df_filtrado.to_excel("dados_filtrados.xlsx", index=False)
    
    nw_auc = df_padronizado[df_padronizado["Código da Conta"].isin(baseclientes["COD"])]
    nw_auc.to_excel("new_auc.xlsx", index=False)
    
    nw_auc["Exposição"] = nw_auc.groupby(["Código da Conta", "RISCO"])["Valor Bruto"].transform("sum")
    nw_auc["Valor-Permitido"] = nw_auc["% Sugerida"] * nw_auc["PL"]
    
    colunas_remover = [
        "Nome da Conta", "Instrumento (Nome)", "Valor Líquido"
    ]
    nw_auc = nw_auc.drop(columns=colunas_remover, errors='ignore')
    
    df_filtrado = nw_auc.drop_duplicates(subset=["Código da Conta", "RISCO"])
    
    df_filtrado["valor-remanescente"] = df_filtrado["Exposição"] - df_filtrado["Valor-Permitido"]
    
    vendedores = df_filtrado[df_filtrado["valor-remanescente"] > 0].reset_index(drop=True)
    
    df_riscos_liquidar = (
        vendedores.groupby("RISCO", as_index=False)["valor-remanescente"]
        .sum()
        .sort_values(by="valor-remanescente", ascending=False)
        .reset_index(drop=True)
    )
    
    df_riscos_liquidar.rename(columns={"valor-remanescente": "ESTOQUE"}, inplace=True)
    
    df_riscos_liquidar["ESTOQUE"] = df_riscos_liquidar["ESTOQUE"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    df_riscos_liquidar = df_riscos_liquidar.reset_index(drop=True, inplace=True)
    
    st.write(df_riscos_liquidar)

    estoque.set_index("RISCO", inplace=True)
    estoque.replace("-", np.nan, inplace=True)
    estoque = estoque.astype(float)
    estoque = estoque.transpose()
    estoque.index = pd.to_datetime(estoque.index)
    estoque = estoque.iloc[:, :7]

    plt.figure(figsize=(12, 6))

    for risco in estoque.columns:
        plt.plot(estoque.index, estoque[risco], marker='o', label=f"Estoque - {risco}")

    for risco in df_riscos_liquidar['RISCO']:
        estoque_risco = df_riscos_liquidar[df_riscos_liquidar['RISCO'] == risco]['ESTOQUE'].values[0]
        plt.scatter(estoque.index[-1], float(estoque_risco.replace("R$", "").replace(",", ".")), color='red', label=f'{risco} - Estoque Atual')

    plt.xlabel("Data")
    plt.ylabel("Valor (R$)")
    plt.title("Variação dos Riscos ao Longo do Tempo")
    plt.legend(loc="upper left", bbox_to_anchor=(1, 1))
    plt.grid(True)
    plt.xticks(rotation=45)
    st.pyplot()


def main():
    st.title("Análise de Carteira de Clientes")
    
    auc_file, status_file, baseclientes_file, estoque_file = upload_files()
    
    if auc_file and status_file and baseclientes_file and estoque_file:
        process_analysis(auc_file, status_file, baseclientes_file, estoque_file)

if __name__ == "__main__":
    main()
