from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

def moeda_curta(valor):

    sinal = "-" if valor < 0 else ""

    valor = abs(valor)

    if valor >= 1_000_000:
        return f"{sinal}R$ {valor/1_000_000:.2f} MM"

    if valor >= 1_000:
        return f"{sinal}R$ {valor/1_000:.0f} mil"

    return f"{sinal}R$ {valor:,.0f}"


def definir_status(situacao):

    texto = str(situacao).lower()

    if (
        "duplicado" in texto
        or "divergente" in texto
    ):
        return "🔴"

    if (
        "somente" in texto
        or "trânsito" in texto
        or "estorno" in texto
    ):
        return "🟡"

    return "✅"


def destacar_situacao(valor):

    texto = str(valor)

    if "Conciliado" in texto:
        return "color: #2ECC71; font-weight: bold;"

    if "Duplicado" in texto:
        return "color: #E74C3C; font-weight: bold;"

    if "Divergente" in texto:
        return "color: #E74C3C; font-weight: bold;"

    return "color: #F39C12; font-weight: bold;"
    
st.markdown("""
<style>

.stApp {
    background-color: #111111;
}

h1 {
    color: white;
    font-weight: 700;
}

h2, h3 {
    color: #E8590C;
}

p, label, span {
    color: white;
}

div[data-testid="metric-container"] {
    background-color: #1A1A1A;
    border: 1px solid #E8590C;
    border-radius: 12px;
    padding: 20px;
}

[data-testid="stMetricValue"] {
    color: #E8590C;
    font-weight: bold;
}

[data-testid="stMetricLabel"] {
    color: #FFFFFF;
    text-transform: uppercase;
}
.stDownloadButton button {
    background-color: #E8590C !important;
    color: white !important;
    border: none !important;
    font-weight: 600 !important;
}

</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent

ARQUIVO = BASE_DIR / "saida" / "conciliacao.xlsx"

st.set_page_config(
    page_title="Conciliação SAP",
    layout="wide"
)

col_titulo, col_download = st.columns([6, 1])

with col_titulo:

    st.markdown("""
    # CONCILIAÇÃO BANCÁRIA

    ### SAP × EXTRATO

    Análise automatizada de reconciliação financeira
    """)

with col_download:
    st.write("")
    st.write("")

if ARQUIVO.exists():

    with open(
        ARQUIVO,
        "rb"
    ) as arquivo_excel:

        st.download_button(
            "📥 Baixar Excel",
            arquivo_excel,
            file_name="conciliacao.xlsx",
            use_container_width=True
        )

else:
    st.error(
        "Relatório não encontrado"
    )

     


detalhe = pd.read_excel(ARQUIVO, sheet_name="Detalhe")
pendencias = pd.read_excel(ARQUIVO, sheet_name="Pendencias")
prova = pd.read_excel(ARQUIVO, sheet_name="Prova_Saldo")

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

# ------------------------------------------------------------ prova de saldo
st.markdown("## 💰 PROVA DE SALDO")

st.caption(
    "Reconciliação consolidada entre razão contábil e extrato bancário"
)

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
    "Saldo Banco",
    "Em Trânsito",
    "Não Lançados",
    "Duplicidades",
    "Divergências",
    "Saldo Contábil",
],
        y=[
            linha["Saldo final extrato"],
            linha["Só no razão (trânsito e estornos)"],
            linha["Só no extrato"],
            linha["Duplicidades no extrato"],
            linha["Valores divergentes"],
            0,  # o Plotly calcula o total acumulado
        ],

        text=[
    moeda_curta(linha["Saldo final extrato"]),
    "",
    "",
    "",
    "",
    moeda_curta(linha["Saldo final razão"]),
],

        textposition="inside",

        increasing={"marker": {"color": "#2E8B57"}},
        decreasing={"marker": {"color": "#C0392B"}},
        totals={"marker": {"color": "#1F4E78"}},
    )
)

fig.update_layout(
    paper_bgcolor="#111111",
    plot_bgcolor="#111111",

    font=dict(
    color="white",
    size=14
),

    title_font=dict(
        size=22,
        color="white"
    ),

    height=420
)

st.plotly_chart(fig, width="stretch")

st.markdown("### AJUSTES DE CONCILIAÇÃO")

col4, col5, col6, col7 = st.columns(4)

with col4:
    st.metric(
        "Em Trânsito",
        moeda_curta(
            linha["Só no razão (trânsito e estornos)"]
        )
    )

with col5:
    st.metric(
        "Não Lançados",
        moeda_curta(
            linha["Só no extrato"]
        )
    )

with col6:
    st.metric(
        "Duplicidades",
        moeda_curta(
            linha["Duplicidades no extrato"]
        )
    )

with col7:
    st.metric(
        "Divergências",
        moeda_curta(
            linha["Valores divergentes"]
        )
    )

nao_explicada = round(
    float(linha["Diferença não explicada"]),
    2
)

if nao_explicada == 0:

    st.success(
        "A ponte fecha: a diferença entre extrato e razão está totalmente explicada."
    )
else:
    st.warning(
        f"Diferença não explicada: R$ {nao_explicada:,.2f}"
    )


# ---------------------------------------------------------------- situações
import plotly.express as px

dados_situacao = (
    detalhe["Situação"]
    .value_counts()
    .reset_index()
)

dados_situacao.columns = [
    "Situação",
    "Quantidade"
]

# remove conciliado
dados_situacao = dados_situacao[
    dados_situacao["Situação"] != "Conciliado"
]

fig_situacoes = px.bar(
    dados_situacao,
    x="Quantidade",
    y="Situação",
    orientation="h",
    text="Quantidade"
)

fig_situacoes.update_traces(
    marker_color="#E8590C",
    textposition="inside"
)

fig_situacoes.update_layout(

    height=350,

    margin=dict(
        l=120,
        r=20,
        t=10,
        b=10
    ),

    paper_bgcolor="#111111",
    plot_bgcolor="#111111",

    font=dict(
        color="white",
        size=14
    ),

    xaxis=dict(
        visible=False
    ),

    yaxis=dict(
        color="white"
    ),

    xaxis_title=None,
    yaxis_title=None,

    title=None,
    showlegend=False
)

st.subheader("📊 Situações Encontradas")

st.plotly_chart(
    fig_situacoes,
    use_container_width=True
)


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

# ------------------------------------------------------------
# EXCEÇÕES
# ------------------------------------------------------------

pendencias_df = detalhe[
    ~detalhe["Situação"].str.contains(
        "Conciliado",
        na=False
    )
]

st.markdown("## 🚨 EXCEÇÕES IDENTIFICADAS")

st.caption(
    "Itens que requerem análise ou ação da tesouraria."
)

pendencias_exibicao = pendencias_df.copy()

pendencias_exibicao.insert(
    0,
    "Status",
    pendencias_exibicao["Situação"].apply(definir_status)
)

col1, col2 = st.columns(2)

with col1:
    st.markdown("🟡 **Pendência de Conciliação**")

with col2:
    st.markdown("🔴 **Divergência / Duplicidade**")

st.dataframe(
    pendencias_exibicao.style.set_properties(
        **{
            "background-color": "#111111",
            "color": "white",
            "border-color": "#666666",
        }
    ),
    width="stretch",
    hide_index=True
)

st.divider()
# ------------------------------------------------------------
# BASE COMPLETA
# ------------------------------------------------------------

st.markdown("## 📋 BASE COMPLETA")

st.caption(
    "Todos os registros utilizados no processo de conciliação."
)

detalhe_exibicao = detalhe.copy()

detalhe_exibicao = detalhe.copy()

def definir_status(situacao):

    texto = str(situacao)

    if "Conciliado" in texto:
        return "✅"

    if "Divergente" in texto:
        return "🔴"

    if "Duplicado" in texto:
        return "🔴"

    return "🟡"

detalhe_exibicao.insert(
    0,
    "Status",
    detalhe_exibicao["Situação"].apply(definir_status)
)

def destacar_situacao(valor):

    texto = str(valor)

    if "Conciliado" in texto:
        return "color: #2ECC71; font-weight: bold;"

    if "Duplicado" in texto:
        return "color: #E74C3C; font-weight: bold;"

    if "Divergente" in texto:
        return "color: #E74C3C; font-weight: bold;"

    return "color: #F39C12; font-weight: bold;"

estilo_tabela = (
    detalhe_exibicao.style
    .set_properties(
        **{
            "background-color": "#111111",
            "color": "white",
            "border-color": "#666666",
        }
    )
    .set_table_styles(
        [
            {
                "selector": "th",
                "props": [
                    ("background-color", "#E8590C"),
                    ("color", "white"),
                    ("font-weight", "bold"),
                ]
            }
        ]
    )
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("🟡 **Pendência**")

with col2:
    st.markdown("🔴 **Divergência / Duplicidade**")

with col3:
    st.markdown("✅ **Conciliado**")

st.dataframe(
    estilo_tabela,
    width="stretch",
    hide_index=True
)

