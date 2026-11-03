import pandas as pd
import streamlit as st
import plotly.graph_objects as go


with open(
    "saida/conciliacao.xlsx",
    "rb"
) as arquivo_excel:

    st.download_button(
        "📥 Baixar Relatório Excel",
        arquivo_excel,
        file_name="conciliacao.xlsx"
    )

st.set_page_config(
    page_title="Conciliação SAP",
    layout="wide"
)

st.title("🏦 Conciliação Bancária SAP x Extrato")

arquivo = "saida/conciliacao.xlsx"

detalhe = pd.read_excel(
    arquivo,
    sheet_name="Detalhe"
)

pendencias = pd.read_excel(
    arquivo,
    sheet_name="Pendencias"
)

prova = pd.read_excel(
    arquivo,
    sheet_name="Prova_Saldo"
)
st.subheader("💰 Prova de Saldo")

conta = st.selectbox(
    "Conta do Razão",
    ["Todas"] +
    sorted(
        prova["Conta do Razão"]
        .astype(str)
        .unique()
        .tolist()
    )
)

if conta == "Todas":

    linha = {
        "Saldo inicial": prova["Saldo inicial"].sum(),
        "Saldo final razão": prova["Saldo final razão"].sum(),
        "Saldo final extrato": prova["Saldo final extrato"].sum(),
        "Só no razão (trânsito e estornos)": prova["Só no razão (trânsito e estornos)"].sum(),
        "Só no extrato": prova["Só no extrato"].sum(),
        "Duplicidades no extrato": prova["Duplicidades no extrato"].sum(),
        "Valores divergentes": prova["Valores divergentes"].sum(),
    }

else:

    linha = prova[
        prova["Conta do Razão"].astype(str) == conta
    ].iloc[0]

# WATERFALL AQUI
fig = go.Figure(
    go.Waterfall(
        orientation="v",

        measure=[
            "absolute",
            "relative",
            "relative",
            "relative",
            "relative",
            "total",
        ],

        x=[
    "Saldo Inicial",
    "Só no Razão",
    "Só no Extrato",
    "Duplicidades",
    "Divergências",
    "Saldo Final"
],

        y=[
    linha["Saldo inicial"],
    linha["Só no razão (trânsito e estornos)"],
    linha["Só no extrato"],
    linha["Duplicidades no extrato"],
    linha["Valores divergentes"],
    0,
],

        increasing={
            "marker": {"color": "#2E8B57"}
        },

        decreasing={
            "marker": {"color": "#C0392B"}
        },

        totals={
            "marker": {"color": "#1F4E78"}
        }
    )
)

fig.update_layout(
    title=(
        "Reconciliação Consolidada"
        if conta == "Todas"
        else f"Reconciliação da Conta {conta}"
    ),

    height=500,
    showlegend=False
)

st.plotly_chart(
    fig,
    use_container_width=True
)
conciliados = detalhe[
    detalhe["Situação"].str.contains(
        "Conciliado",
        na=False
    )
]

taxa_conciliacao = round(
    len(conciliados) / len(detalhe) * 100,
    2
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Taxa de Conciliação",
        f"{taxa_conciliacao}%"
    )

with col2:
    st.metric(
        "Registros",
        len(detalhe)
    )

with col3:
    st.metric(
        "Pendências",
        len(pendencias)
    )

valor_razao = detalhe["Valor razão"].sum()

valor_extrato = detalhe["Valor extrato"].sum()

valor_diferenca = detalhe["Diferença (razão - extrato)"].abs().sum()


st.divider()

st.subheader("📊 Situações Encontradas")

situacoes = (
    detalhe["Situação"]
    .value_counts()
)

st.bar_chart(situacoes)

filtro = st.selectbox(
    "Filtrar Situação",
    ["Todas"] +
    sorted(
        detalhe["Situação"]
        .dropna()
        .unique()
        .tolist()
    )
)

conta_selecionada = st.selectbox(
    "Conta Corrente",
    ["Todas"] +
    sorted(
        detalhe["Conta corrente"]
        .astype(str)
        .unique()
        .tolist()
    )
)

if conta_selecionada != "Todas":

    detalhe = detalhe[
        detalhe["Conta corrente"].astype(str)
        == conta_selecionada
    ]

if filtro != "Todas":
    detalhe = detalhe[
        detalhe["Situação"] == filtro
    ]

st.subheader("📋 Detalhamento da Conciliação")

st.dataframe(
    detalhe,
    use_container_width=True,
    hide_index=True
)