
import pandas as pd
import re
import streamlit as st
import io

st.set_page_config(page_title="Filtro e padronização da conta corrente dos clientes com custódias no Itau", page_icon="📈", layout="wide")

st.title("📈 Padronização da conta corrente clientes Itau")

df = st.file_uploader("Upload da base para o tratamento", type="xlsx")

def tratamento(df):
    clientes = []
    cliente_atual = {}

    for _, row in df.iterrows():
        linha = str(row[0]).strip()

        if linha.startswith("Agência/Conta"):
            if cliente_atual:
                clientes.append(cliente_atual)

            match = re.search(r"Agência/Conta:\s*(\d+)\s*/\s*(\d+)-(\d+)\s*(.*)", linha)
            if match:
                agencia, conta, digito, nome = match.groups()
                nome = nome.lstrip("-").strip()

                cliente_atual = {
                    "Agência": agencia,
                    "Conta": f"{conta}-{digito}",  
                    "Nome": nome,
                    "Saldo Disponível para Aplicação Hoje": 0
                }
        else:
            if "SDO DISP P/ APLIC HOJE S/CPMF" in linha:
                try:
                    valor = str(row[3]).strip()
                    cliente_atual["Saldo Disponível para Aplicação Hoje"] = valor
                except (IndexError, ValueError):
                    cliente_atual["Saldo Disponível para Aplicação Hoje"] = 0

    if cliente_atual:
        clientes.append(cliente_atual)

    df_clientes = pd.DataFrame(clientes)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_clientes.to_excel(writer, index=False, sheet_name='Irregulares')
    output.seek(0)

    st.download_button(
                label="📥 Baixar resultado em Excel",
                data=output,
                file_name="df_clientes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
