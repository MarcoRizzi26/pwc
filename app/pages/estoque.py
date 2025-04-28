import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

# Função para o upload dos arquivos
def upload_files():
    auc_file = st.file_uploader("Upload do arquivo AUC", type=["xlsx"])
    status_file = st.file_uploader("Upload do arquivo Status", type=["xlsx"])
    baseclientes_file = st.file_uploader("Upload do arquivo Base de Clientes", type=["xlsx"])
    estoque_file = st.file_uploader("Upload do arquivo Estoque Consolidado", type=["xlsx"])
    
    return auc_file, status_file, baseclientes_file, estoque_file

# Função para processar e realizar a análise
def process_analysis(auc_file, status_file, baseclientes_file, estoque_file):
    # Carregar os arquivos
    auc = pd.read_excel(auc_file)
    status = pd.read_excel(status_file)
    baseclientes = pd.read_excel(baseclientes_file)
    estoque = pd.read_excel(estoque_file)
    
    # Realizar o processamento da análise AUC
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
    
    # Salvar os dados filtrados
    df_filtrado.to_excel("dados_filtrados.xlsx", index=False)
    
    nw_auc = df_padronizado[df_padronizado["Código da Conta"].isin(baseclientes["COD"])]
    nw_auc.to_excel("new_auc.xlsx", index=False)
    
    # Realizar mais análises
    nw_auc["Exposição"] = nw_auc.groupby(["Código da Conta", "RISCO"])["Valor Bruto"].transform("sum")
    nw_auc["Valor-Permitido"] = nw_auc["% Sugerida"] * nw_auc["PL"]
    
    colunas_remover = [
        "Nome da Conta", "Instrumento (Nome)", "Valor Líquido"
    ]
    nw_auc = nw_auc.drop(columns=colunas_remover, errors='ignore')
    
    df_filtrado = nw_auc.drop_duplicates(subset=["Código da Conta", "RISCO"])
    
    # Calcular o valor remanescente
    df_filtrado["valor-remanescente"] = df_filtrado["Exposição"] - df_filtrado["Valor-Permitido"]
    
    # Filtrar os vendedores
    vendedores = df_filtrado[df_filtrado["valor-remanescente"] > 0].reset_index(drop=True)
    
    # Agrupar os riscos a serem liquidados
    df_riscos_liquidar = (
        vendedores.groupby("RISCO", as_index=False)["valor-remanescente"]
        .sum()
        .sort_values(by="valor-remanescente", ascending=False)
        .reset_index(drop=True)
    )
    
    df_riscos_liquidar.rename(columns={"valor-remanescente": "ESTOQUE"}, inplace=True)
    
    df_riscos_liquidar["ESTOQUE"] = df_riscos_liquidar["ESTOQUE"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    df_riscos_liquidar = df_riscos_liquidar.reset_index(drop=True, inplace=True)
    
    # Mostrar df_riscos_liquidar
    st.write(df_riscos_liquidar)

    # Processar o estoque
    estoque.set_index("RISCO", inplace=True)
    estoque.replace("-", np.nan, inplace=True)
    estoque = estoque.astype(float)
    estoque = estoque.transpose()
    estoque.index = pd.to_datetime(estoque.index)
    estoque = estoque.iloc[:, :7]

    # Adicionar os dados de df_riscos_liquidar ao gráfico
    plt.figure(figsize=(12, 6))

    # Plotar os dados do estoque (valores históricos)
    for risco in estoque.columns:
        plt.plot(estoque.index, estoque[risco], marker='o', label=f"Estoque - {risco}")

    # Plotar os valores de estoque do df_riscos_liquidar (valores atuais do risco)
    for risco in df_riscos_liquidar['RISCO']:
        estoque_risco = df_riscos_liquidar[df_riscos_liquidar['RISCO'] == risco]['ESTOQUE'].values[0]
        plt.scatter(estoque.index[-1], float(estoque_risco.replace("R$", "").replace(",", ".")), color='red', label=f'{risco} - Estoque Atual')

    # Configurações do gráfico
    plt.xlabel("Data")
    plt.ylabel("Valor (R$)")
    plt.title("Variação dos Riscos ao Longo do Tempo")
    plt.legend(loc="upper left", bbox_to_anchor=(1, 1))
    plt.grid(True)
    plt.xticks(rotation=45)
    st.pyplot()


# Função principal do Streamlit
def main():
    st.title("Análise de Carteira de Clientes")
    
    # Upload dos arquivos
    auc_file, status_file, baseclientes_file, estoque_file = upload_files()
    
    # Se os arquivos forem carregados, processar a análise
    if auc_file and status_file and baseclientes_file and estoque_file:
        process_analysis(auc_file, status_file, baseclientes_file, estoque_file)

if __name__ == "__main__":
    main()
