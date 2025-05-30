import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(layout="wide", page_title="Relatório de Fundos")

st.title("📊 Relatório de Aplicações e Resgates por Fundo")

# Upload de arquivos
st.header("📁 Upload de Arquivos")
col1, col2 = st.columns(2)

with col1:
    nome_fundos_file = st.file_uploader("Upload do arquivo 'NOME-FUNDOS.xlsx'", type='xlsx')

with col2:
    auc_file = st.file_uploader("Upload do arquivo 'AUC - xx.xx.xxxx.xlsx'", type='xlsx')

aplicacoes_files = st.file_uploader("Upload de arquivos de aplicações (.xlsx)", type="xlsx", accept_multiple_files=True)
resgates_files = st.file_uploader("Upload de arquivos de resgates (.xlsx)", type="xlsx", accept_multiple_files=True)

def padronizar_cnpj(cnpj):
    return str(cnpj).replace(',', '').strip().zfill(14)

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

if nome_fundos_file and auc_file and aplicacoes_files and resgates_files:
    # Leitura de arquivos
    nome_fundos = pd.read_excel(nome_fundos_file)
    auc = pd.read_excel(auc_file)
    aplicacoes = pd.concat([pd.read_excel(f) for f in aplicacoes_files], ignore_index=True)
    resgates = pd.concat([pd.read_excel(f) for f in resgates_files], ignore_index=True)

    # Separar RT dos outros tipos
    resgates_rt = resgates[resgates['tipo de resgate'] == 'RT'].copy()
    resgates_others = resgates[resgates['tipo de resgate'] != 'RT'].copy()

    # Padronizar strings
    resgates_rt['cnpj do fundo'] = resgates_rt['cnpj do fundo'].astype(str).str.replace(',', '').str.strip()
    resgates_rt['número da conta'] = resgates_rt['número da conta'].astype(str).str.strip()
    auc['Instrumento (Símbolo)'] = auc['Instrumento (Símbolo)'].astype(str).str.strip()
    auc['Código da Conta'] = auc['Código da Conta'].astype(str).str.strip()

    # Merge RT com AUC
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

    # Padronização de CNPJs
    aplicacoes['cnpj do fundo'] = aplicacoes['cnpj do fundo'].apply(padronizar_cnpj)
    resgates_final['cnpj do fundo'] = resgates_final['cnpj do fundo'].apply(padronizar_cnpj)
    nome_fundos['CNPJ'] = nome_fundos['CNPJ'].apply(padronizar_cnpj)
    nome_fundos = nome_fundos.drop_duplicates(subset='CNPJ')

    # Merge com nome do fundo
    aplicacoes_com_nome = aplicacoes.merge(nome_fundos[['CNPJ', 'Nome do Fundo']],
                                           left_on='cnpj do fundo', right_on='CNPJ', how='left')
    resgates_com_nome = resgates_final.merge(nome_fundos[['CNPJ', 'Nome do Fundo']],
                                             left_on='cnpj do fundo', right_on='CNPJ', how='left')

    # Agrupamento por fundo
    aplicacoes_por_fundo = aplicacoes_com_nome.groupby('Nome do Fundo')['valor da aplicacao'].sum().reset_index()
    resgates_por_fundo = resgates_com_nome.groupby('Nome do Fundo')['valor do resgate'].sum().reset_index()
    relatorio = pd.merge(aplicacoes_por_fundo, resgates_por_fundo, on='Nome do Fundo', how='outer').fillna(0)

    # Cálculo do NNM
    relatorio['NNM'] = relatorio['valor da aplicacao'] - relatorio['valor do resgate']

    # Formatar colunas monetárias
    relatorio['valor da aplicacao (R$)'] = relatorio['valor da aplicacao'].apply(formatar_moeda)
    relatorio['valor do resgate (R$)'] = relatorio['valor do resgate'].apply(formatar_moeda)
    relatorio['NNM (R$)'] = relatorio['NNM'].apply(formatar_moeda)

    st.success("✅ Relatório consolidado com sucesso!")

    # Exibir tabela
    st.subheader("📄 Tabela Consolidada")
    st.dataframe(relatorio[['Nome do Fundo', 'valor da aplicacao (R$)', 'valor do resgate (R$)', 'NNM (R$)']])

    # Gráfico com valores
    st.subheader("📈 Gráfico Comparativo")
    fig, ax = plt.subplots(figsize=(12, 6))

    barras_ap = ax.bar(relatorio['Nome do Fundo'], relatorio['valor da aplicacao'], label='Aplicações', color='green')
    barras_reg = ax.bar(relatorio['Nome do Fundo'], relatorio['valor do resgate'], label='Resgates', color='red', alpha=0.7)

    # Adicionar rótulos nas barras com melhor posicionamento
    def adicionar_valores(barras):
        for barra in barras:
            altura = barra.get_height()
            ax.annotate(f"R$ {altura:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."),
                        xy=(barra.get_x() + barra.get_width() / 2, altura),
                        xytext=(0, 10),  # distância maior acima da barra
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9, fontweight='bold', color='black')

    adicionar_valores(barras_ap)
    adicionar_valores(barras_reg)

    # Ajustar espaçamento do topo para não cortar os rótulos
    ax.set_ylim(top=max(relatorio['valor da aplicacao'].max(), relatorio['valor do resgate'].max()) * 1.15)

    ax.set_title('Aplicações vs Resgates por Fundo')
    ax.set_ylabel('Valor (R$)')
    ax.legend()
    plt.xticks(rotation=45, ha='right')
    st.pyplot(fig)


else:
    st.info("📥 Faça upload de todos os arquivos para gerar o relatório. V2")
