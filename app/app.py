import streamlit as st
import pandas as pd

st.set_page_config(page_title="Verificador de Produtos Irregulares", layout="centered")

st.title("🔍 Verificador de Produtos Irregulares (PWC vs AUC)")

st.markdown("""
Este app compara os produtos autorizados por cliente (PWC) com a carteira atual (AUC) 
para identificar **produtos irregulares** que não estão na lista aprovada.
""")

pwc_file = st.file_uploader("📤 Faça upload do arquivo **PWC (.xlsx)**", type=["xlsx"])
auc_file = st.file_uploader("📤 Faça upload do arquivo **AUC (.xlsx)**", type=["xlsx"])

if pwc_file and auc_file:
    pwc = pd.read_excel(pwc_file)
    auc = pd.read_excel(auc_file)

    # Renomeia colunas para facilitar o join
    pwc_renamed = pwc.rename(columns={"Cód.": "Codigo da Conta", "PRODUTO APROVADO": "Instrumento (Nome)"})
    auc = auc.rename(columns={"Código da Conta": "Codigo da Conta"})

    # Filtra o auc para conter apenas os clientes da base PWC
    clientes_pwc = pwc_renamed["Codigo da Conta"].unique()
    auc_filtrado = auc[auc["Codigo da Conta"].isin(clientes_pwc)]

    # Merge para identificar produtos REGULARES (autorizados)
    merged = pd.merge(
        auc_filtrado,
        pwc_renamed[["Codigo da Conta", "Instrumento (Nome)"]],
        on=["Codigo da Conta", "Instrumento (Nome)"],
        how="left",
        indicator=True
    )

    # Produtos que estão na carteira dos clientes PWC mas NÃO foram aprovados
    irregulares = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])

    # Filtro de produtos irrelevantes
    filtro = ~irregulares["Instrumento (Nome)"].str.contains("BRL|Taxa de Gestão -", regex=True, na=False)
    clientes_com_bloqueio_filtrado = irregulares[filtro].copy()

    st.success("✅ Análise concluída! Veja os produtos irregulares abaixo:")
    st.dataframe(clientes_com_bloqueio_filtrado[["Codigo da Conta", "Nome da Conta", "Instrumento (Nome)", "Valor Bruto"]])

    # Opção de download
    st.download_button(
        label="📥 Baixar resultado em Excel",
        data=clientes_com_bloqueio_filtrado.to_excel(index=False, engine="openpyxl"),
        file_name="clientes_com_bloqueio_filtrado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("⬆️ Faça upload dos dois arquivos para iniciar a análise.")
