from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ARQUIVO = Path("saida/conciliacao.xlsx")

st.set_page_config(
    page_title="Conciliação SAP",
    layout="wide"
)

st.title("🏦 Conciliação Bancária SAP x Extrato")

# Sem o relatório não há o que mostrar: avisa em vez de quebrar com um erro
if not ARQUIVO.exists():
    st.error(
        f"Relatório não encontrado em `{ARQUIVO}`. "
        "Rode `python main.py` antes para gerá-lo."
    )
    st.stop()

st.download_button(
    "📥 Baixar Relatório Excel",
    ARQUIVO.read_bytes(),
    file_name="conciliacao.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

detalhe = pd.read_excel(ARQUIVO, sheet_name="Detalhe")
pendencias = pd.read_excel(ARQUIVO, sheet_name="Pendencias")
prova = pd.read_excel(ARQUIVO, sheet_name="Prova_Saldo")

# ------------------------------------------------------------ prova de saldo
st.subheader("💰 Prova de Saldo")

conta = st.selectbox(
    "Conta do Razão",
    ["Todas"] + sorted(prova["Conta do Razão"].astype(str).unique().tolist())
)

if conta == "Todas":
    colunas_soma = [
        "Saldo final razão",
        "Saldo final extrato",
        "Só no razão (trânsito e estornos)",
        "Só no extrato",
        "Duplicidades no extrato",
        "Valores divergentes",
        "Diferença não explicada",
    ]
    linha = {c: prova[c].sum() for c in colunas_soma}
else:
    linha = prova[prova["Conta do Razão"].astype(str) == conta].iloc[0]

# Ponte entre os dois saldos: extrato + pendências = razão.
# (O saldo inicial é igual nos dois lados, então não entra na ponte.)
fig = go.Figure(
    go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "relative", "total"],
        x=[
            "Saldo final extrato",
            "Só no razão",
            "Só no extrato",
            "Duplicidades",
            "Divergências",
            "Saldo final razão",
        ],
        y=[
            linha["Saldo final extrato"],
            linha["Só no razão (trânsito e estornos)"],
            linha["Só no extrato"],
            linha["Duplicidades no extrato"],
            linha["Valores divergentes"],
            0,  # o Plotly calcula o total acumulado
        ],
        increasing={"marker": {"color": "#2E8B57"}},
        decreasing={"marker": {"color": "#C0392B"}},
        totals={"marker": {"color": "#1F4E78"}},
    )
)

fig.update_layout(
    title=(
        "Conciliação Consolidada"
        if conta == "Todas"
        else f"Conciliação da Conta {conta}"
    ),
    height=500,
    showlegend=False,
)

st.plotly_chart(fig, width="stretch")

nao_explicada = round(float(linha["Diferença não explicada"]), 2)
if nao_explicada == 0:
    st.success("A ponte fecha: a diferença entre extrato e razão está totalmente explicada.")
else:
    st.warning(f"Diferença não explicada: R$ {nao_explicada:,.2f}")

# ------------------------------------------------------------------ métricas
conciliados = detalhe[detalhe["Situação"].str.contains("Conciliado", na=False)]
taxa_conciliacao = round(len(conciliados) / len(detalhe) * 100, 2)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Taxa de Conciliação", f"{taxa_conciliacao}%")

with col2:
    st.metric("Registros", len(detalhe))

with col3:
    st.metric("Pendências", len(pendencias))

st.divider()

# ---------------------------------------------------------------- situações
st.subheader("📊 Situações Encontradas")

st.bar_chart(detalhe["Situação"].value_counts())

filtro = st.selectbox(
    "Filtrar Situação",
    ["Todas"] + sorted(detalhe["Situação"].dropna().unique().tolist())
)

conta_selecionada = st.selectbox(
    "Conta Corrente",
    ["Todas"] + sorted(detalhe["Conta corrente"].astype(str).unique().tolist())
)

if conta_selecionada != "Todas":
    detalhe = detalhe[detalhe["Conta corrente"].astype(str) == conta_selecionada]

if filtro != "Todas":
    detalhe = detalhe[detalhe["Situação"] == filtro]

st.subheader("📋 Detalhamento da Conciliação")

st.dataframe(detalhe, width="stretch", hide_index=True)
