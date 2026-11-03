"""Conciliação bancária: razão contábil (SAP) x extrato bancário.

Todos os dados usados neste projeto são fictícios.

Regras aplicadas, nesta ordem:
  0. Estornos no razão: lançamento e estorno (mesma referência, valores opostos).
  1. Conciliação por valor exato + data dentro da tolerância.
  2. Duplicidade no extrato: mesmo valor, data e histórico de um item já conciliado.
  3. Valor divergente: mesma contraparte e data próxima, mas valores diferentes.
  4. O que sobrar: pendências só no razão (em trânsito) ou só no extrato.
"""
import re
import unicodedata

import pandas as pd

from src.constants import *

from src.loaders import (
    carregar,
    contraparte,
    _centavos
)


# ---------------------------------------------------------------- leitura



# ------------------------------------------------------------ conciliação

def _linha(situacao, a=None, b=None, dias=None) -> dict:
    """Monta uma linha do resultado. a = lançamento do razão, b = do extrato."""
    base = a if a is not None else b
    return {
        "conta_razao": base["conta_razao"],
        "conta": base["conta"],
        "situacao": situacao,
        "doc_razao": a["id"] if a is not None else None,
        "_ids_extrato": [b["id"]] if b is not None else [],
        "data_razao": a["data"] if a is not None else pd.NaT,
        "data_extrato": b["data"] if b is not None else pd.NaT,
        "dias_diferenca": dias,
        "valor_razao": a["valor"] if a is not None else 0.0,
        "valor_extrato": b["valor"] if b is not None else 0.0,
        "texto_razao": a["texto"] if a is not None else "",
        "texto_extrato": b["texto"] if b is not None else "",
    }


def _acao(linha: pd.Series) -> str:
    s = linha["situacao"]
    if s == CONCILIADO:
        return ""
    if s == DATA_DIVERGENTE:
        return "Sem ajuste: diferença de data (timing) entre lançamento e banco."
    if s == DUPLICADO:
        return "Solicitar ao banco o estorno do lançamento em duplicidade."
    if s == VALOR_DIVERGENTE:
        return ("Investigar a diferença com o fornecedor/cliente e ajustar o razão "
                "ou contestar o valor com o banco.")
    if s == SO_EXTRATO:
        texto = str(linha["texto_extrato"]).upper()
        for palavra, categoria in CATEGORIAS_EXTRATO:
            if palavra in texto:
                return f"Lançar no razão: {categoria}."
        return "Identificar a origem e lançar no razão."
    if s == DEP_TRANSITO:
        return "Acompanhar a compensação no próximo extrato; se não vier, investigar."
    if s == PAG_TRANSITO:
        return "Acompanhar a compensação no próximo extrato (pagamento em circulação)."
    if s in (ESTORNADO, ESTORNO):
        return "Sem efeito no saldo: lançamento e estorno se anulam."
    return ""


def conciliar(razao: pd.DataFrame, extrato: pd.DataFrame,
              tol_dias: int = TOLERANCIA_DIAS,
              tol_valor_pct: float = TOLERANCIA_VALOR_PCT) -> pd.DataFrame:
    """Concilia razão x extrato e devolve uma linha por evento."""
    r = razao.to_dict("records")
    e = extrato.to_dict("records")
    usados_r, usados_e = set(), set()
    linhas = []
    linha_do_extrato = {}   # posição no extrato -> linha do resultado (para duplicidades)

    # 0. Estornos dentro do razão: mesma referência e valores opostos
    for i, a in enumerate(r):
        if i in usados_r or pd.isna(a["ref"]):
            continue
        for j, b in enumerate(r):
            if j <= i or j in usados_r:
                continue
            if (b["conta"] == a["conta"] and b["ref"] == a["ref"]
                    and b["centavos"] == -a["centavos"]):
                a_eh_estorno = str(a["texto"]).upper().startswith("ESTORNO") or (
                    not str(b["texto"]).upper().startswith("ESTORNO") and a["data"] > b["data"])
                original, estorno = (b, a) if a_eh_estorno else (a, b)
                linhas.append(_linha(ESTORNADO, original))
                linhas.append(_linha(ESTORNO, estorno))
                usados_r.update({i, j})
                break

    # 1. Valor exato + data dentro da tolerância (prefere mesma contraparte, depois data)
    for i in sorted(range(len(r)), key=lambda k: r[k]["data"]):
        if i in usados_r:
            continue
        a = r[i]
        melhor = None
        for j, b in enumerate(e):
            if j in usados_e or b["conta"] != a["conta"] or b["centavos"] != a["centavos"]:
                continue
            dias = abs((b["data"] - a["data"]).days)
            if dias > tol_dias:
                continue
            mesmo_nome = a["contraparte"] != "" and a["contraparte"] == b["contraparte"]
            chave = (not mesmo_nome, dias)
            if melhor is None or chave < melhor[0]:
                melhor = (chave, j, dias)
        if melhor:
            _, j, dias = melhor
            situacao = CONCILIADO if dias == 0 else DATA_DIVERGENTE
            linhas.append(_linha(situacao, a, e[j], dias))
            linha_do_extrato[j] = linhas[-1]
            usados_r.add(i)
            usados_e.add(j)

    # 2. Duplicidade no extrato: igual (conta, valor, data, histórico) a um item já conciliado
    for j, b in enumerate(e):
        if j in usados_e:
            continue
        for k, linha in linha_do_extrato.items():
            o = e[k]
            if (o["conta"] == b["conta"] and o["centavos"] == b["centavos"]
                    and o["data"] == b["data"] and o["texto"] == b["texto"]):
                linha["situacao"] = DUPLICADO
                linha["_ids_extrato"].append(b["id"])
                linha["valor_extrato"] = round(linha["valor_extrato"] + b["valor"], 2)
                usados_e.add(j)
                break

    # 3. Valor divergente: mesma contraparte, mesmo sinal, data próxima, valor parecido
    for i, a in enumerate(r):
        if i in usados_r or a["contraparte"] == "":
            continue
        melhor = None
        for j, b in enumerate(e):
            if j in usados_e or b["conta"] != a["conta"] or b["contraparte"] != a["contraparte"]:
                continue
            if a["centavos"] * b["centavos"] <= 0:
                continue
            dias = abs((b["data"] - a["data"]).days)
            dif_pct = abs(a["centavos"] - b["centavos"]) / abs(a["centavos"])
            if dias > tol_dias or dif_pct > tol_valor_pct:
                continue
            chave = (dias, dif_pct)
            if melhor is None or chave < melhor[0]:
                melhor = (chave, j, dias)
        if melhor:
            _, j, dias = melhor
            linhas.append(_linha(VALOR_DIVERGENTE, a, e[j], dias))
            usados_r.add(i)
            usados_e.add(j)

    # 4. Pendências: o que sobrou de cada lado
    for i, a in enumerate(r):
        if i not in usados_r:
            linhas.append(_linha(DEP_TRANSITO if a["centavos"] > 0 else PAG_TRANSITO, a))
    for j, b in enumerate(e):
        if j not in usados_e:
            linhas.append(_linha(SO_EXTRATO, None, b))

    # Resultado final
    for linha in linhas:
        linha["doc_extrato"] = " / ".join(str(x) for x in sorted(linha.pop("_ids_extrato")))
    df = pd.DataFrame(linhas)
    df["doc_razao"] = df["doc_razao"].astype("Int64")
    df["dias_diferenca"] = df["dias_diferenca"].astype("Int64")
    df["diferenca"] = (df["valor_razao"] - df["valor_extrato"]).round(2)
    df["acao"] = df.apply(_acao, axis=1)
    df["_data_ref"] = df["data_razao"].fillna(df["data_extrato"])
    df = df.sort_values(["conta_razao", "_data_ref", "doc_extrato"]).drop(columns="_data_ref")
    return df.reset_index(drop=True)


# ----------------------------------------------------------- prova de saldo

def prova_de_saldo(resultado: pd.DataFrame, contas: pd.DataFrame) -> pd.DataFrame:
    """Mostra que a diferença de saldo é explicada pelos itens não conciliados."""
    col_inicial = next(c for c in contas.columns if str(c).startswith("Saldo inicial"))
    saldo_inicial = dict(zip(contas["Conta do Razão"], contas[col_inicial]))
    linhas = []
    for conta, g in resultado.groupby("conta_razao"):
        inicial = saldo_inicial[conta]
        saldo_razao = inicial + g["valor_razao"].sum()
        saldo_extrato = inicial + g["valor_extrato"].sum()
        diferenca = saldo_razao - saldo_extrato

        def soma(situacoes):
            return g.loc[g["situacao"].isin(situacoes), "diferenca"].sum()

        so_razao = soma(SITUACOES_SO_RAZAO)
        so_extrato = soma([SO_EXTRATO])
        duplicados = soma([DUPLICADO])
        divergentes = soma([VALOR_DIVERGENTE])
        linhas.append({
            "Conta do Razão": conta,
            "Saldo inicial": inicial,
            "Saldo final razão": saldo_razao,
            "Saldo final extrato": saldo_extrato,
            "Diferença (razão - extrato)": diferenca,
            "Só no razão (trânsito e estornos)": so_razao,
            "Só no extrato": so_extrato,
            "Duplicidades no extrato": duplicados,
            "Valores divergentes": divergentes,
            "Diferença não explicada": diferenca - (so_razao + so_extrato + duplicados + divergentes),
        })
    return pd.DataFrame(linhas).round(2)


# ---------------------------------------------------------------- validação

def validar_contra_gabarito(resultado: pd.DataFrame, caminho: str):
    """Compara o resultado com a aba Gabarito (usada só para conferir, nunca na lógica).

    Devolve (total de linhas do gabarito, acertos, tabela com as divergências).
    """
    gab = pd.read_excel(caminho, sheet_name="Gabarito", dtype={"Nº Documento Extrato": str})
    esperado = {}
    for _, g in gab.iterrows():
        doc_sap = int(g["Nº Documento SAP"]) if pd.notna(g["Nº Documento SAP"]) else 0
        doc_ext = "" if pd.isna(g["Nº Documento Extrato"]) else re.sub(
            r"\.0\b", "", str(g["Nº Documento Extrato"]))
        esperado[(int(g["Conta do Razão"]), doc_sap, doc_ext)] = g["Situação esperada"]

    obtido = {}
    for _, x in resultado.iterrows():
        doc_sap = 0 if pd.isna(x["doc_razao"]) else int(x["doc_razao"])
        obtido[(int(x["conta_razao"]), doc_sap, x["doc_extrato"])] = x["situacao"]

    divergencias = []
    for chave, situacao in esperado.items():
        if obtido.get(chave) != situacao:
            divergencias.append({"conta": chave[0], "doc_sap": chave[1], "doc_extrato": chave[2],
                                 "esperado": situacao, "obtido": obtido.get(chave, "(não encontrado)")})
    extras = [k for k in obtido if k not in esperado]
    for chave in extras:
        divergencias.append({"conta": chave[0], "doc_sap": chave[1], "doc_extrato": chave[2],
                             "esperado": "(fora do gabarito)", "obtido": obtido[chave]})
    total = len(esperado)
    acertos = total - sum(1 for d in divergencias if d["esperado"] != "(fora do gabarito)")
    return total, acertos, pd.DataFrame(divergencias)


# ------------------------------------------------------------------ Excel

COLUNAS_DETALHE = {
    "conta_razao": "Conta do Razão", "conta": "Conta corrente", "situacao": "Situação",
    "doc_razao": "Nº Doc. SAP", "doc_extrato": "Nº Doc. Extrato",
    "data_razao": "Data razão", "data_extrato": "Data extrato",
    "dias_diferenca": "Dias de diferença", "valor_razao": "Valor razão",
    "valor_extrato": "Valor extrato", "diferenca": "Diferença (razão - extrato)",
    "texto_razao": "Texto razão", "texto_extrato": "Histórico extrato", "acao": "Ação sugerida",
}


def exportar_excel(resultado: pd.DataFrame, prova: pd.DataFrame, caminho: str) -> None:
    """Grava o relatório em Excel: Resumo, Prova_Saldo, Detalhe e Pendencias."""
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    detalhe = resultado.rename(columns=COLUNAS_DETALHE)[list(COLUNAS_DETALHE.values())]
    pendencias = detalhe[detalhe["Situação"].isin(SITUACOES_COM_ACAO)]
    resumo = pd.crosstab(resultado["situacao"], resultado["conta_razao"],
                         margins=True, margins_name="Total")
    resumo.index.name = "Situação"
    resumo.columns = [str(c) for c in resumo.columns]

    with pd.ExcelWriter(caminho, engine="openpyxl") as xl:
        resumo.to_excel(xl, sheet_name="Resumo")
        prova.to_excel(xl, sheet_name="Prova_Saldo", index=False)
        detalhe.to_excel(xl, sheet_name="Detalhe", index=False)
        pendencias.to_excel(xl, sheet_name="Pendencias", index=False)

        cabecalho = PatternFill("solid", start_color="1F3864")
        for ws in xl.book.worksheets:
            for celula in ws[1]:
                celula.font = Font(name="Arial", bold=True, color="FFFFFF", size=10)
                celula.fill = cabecalho
                celula.alignment = Alignment(wrap_text=True, vertical="center")
            titulos = [c.value for c in ws[1]]
            for linha in ws.iter_rows(min_row=2):
                for celula, titulo in zip(linha, titulos):
                    celula.font = Font(name="Arial", size=10)
                    t = str(titulo)
                    if t.startswith(("Valor", "Diferença (", "Saldo", "Só no", "Duplicidades",
                                     "Valores", "Diferença não")):
                        celula.number_format = "#,##0.00;(#,##0.00);-"
                    elif t.startswith("Data"):
                        celula.number_format = "dd/mm/yyyy"
            for i, titulo in enumerate(titulos, start=1):
                largura = max(len(str(titulo)), *(len(str(c.value or "")) for c in ws[get_column_letter(i)]))
                ws.column_dimensions[get_column_letter(i)].width = min(largura + 2, 60)
            ws.freeze_panes = "A2"
