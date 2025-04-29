import streamlit as st
import pandas as pd
import io


st.set_page_config(page_title="Verificador de Produtos Irregulares", layout="centered")

st.title("🔍 Verificador de Produtos Irregulares PWC")

st.markdown("""
Este app compara os produtos autorizados por cliente (PWC) com a carteira atual (AUC) 
para identificar **produtos irregulares** que não estão na lista aprovada.
""")

pwc_file = st.file_uploader("📤 Faça upload do arquivo **PWC (.xlsx)**", type=["xlsx"])
auc_file = st.file_uploader("📤 Faça upload do arquivo **AUC (.xlsx)**", type=["xlsx"])

def show(pwc_file, auc_file):
    if pwc_file and auc_file:
        try:
            pwc = pd.read_excel(pwc_file)
            auc = pd.read_excel(auc_file)

            pwc_renamed = pwc.rename(columns={"Cód.": "Codigo da Conta", "PRODUTO APROVADO": "Instrumento (Nome)"})
            auc = auc.rename(columns={"Código da Conta": "Codigo da Conta"})

            clientes_pwc = pwc_renamed["Codigo da Conta"].unique()
            auc_filtrado = auc[auc["Codigo da Conta"].isin(clientes_pwc)]

            merged = pd.merge(
                auc_filtrado,
                pwc_renamed[["Codigo da Conta", "Instrumento (Nome)"]],
                on=["Codigo da Conta", "Instrumento (Nome)"],
                how="left",
                indicator=True
            )

            irregulares = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])

            filtro = ~irregulares["Instrumento (Nome)"].str.contains("BRL|Taxa de Gestão -", regex=True, na=False)
            clientes_com_bloqueio_filtrado = irregulares[filtro].copy()

            clientes_com_bloqueio_filtrado = clientes_com_bloqueio_filtrado.reset_index(drop=True)

            st.success("✅ Análise concluída! Veja os produtos irregulares abaixo:")
            st.dataframe(clientes_com_bloqueio_filtrado[["Codigo da Conta", "Nome da Conta", "Instrumento (Nome)", "Valor Bruto"]])

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                clientes_com_bloqueio_filtrado.to_excel(writer, index=False, sheet_name='Irregulares')
            output.seek(0)

            st.download_button(
                label="📥 Baixar resultado em Excel",
                data=output,
                file_name="clientes_com_bloqueio_filtrado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Ocorreu um erro ao processar os arquivos: {str(e)}")

    else:
        st.info("⬆️ Faça upload dos dois arquivos para iniciar a análise.")
