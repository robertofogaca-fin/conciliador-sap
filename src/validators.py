import re

import pandas as pd

from src.constants import *

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


