from collections import defaultdict

import pandas as pd

from src.constants import (
    CATEGORIAS_EXTRATO,
    CONCILIADO,
    DATA_DIVERGENTE,
    DEP_TRANSITO,
    DUPLICADO,
    ESTORNADO,
    ESTORNO,
    PAG_TRANSITO,
    SO_EXTRATO,
    TOLERANCIA_DIAS,
    TOLERANCIA_VALOR_PCT,
    VALOR_DIVERGENTE,
)


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

    # Índices: cada busca olha só os candidatos possíveis, em vez de percorrer a lista toda
    # (sem eles, o custo cresce com o quadrado do número de linhas)
    por_referencia = defaultdict(list)   # (conta, referência) -> posições no razão
    for i, a in enumerate(r):
        if not pd.isna(a["conta"]) and not pd.isna(a["ref"]):
            por_referencia[(a["conta"], a["ref"])].append(i)
    por_valor = defaultdict(list)        # (conta, centavos) -> posições no extrato
    por_contraparte = defaultdict(list)  # (conta, contraparte) -> posições no extrato
    for j, b in enumerate(e):
        if not pd.isna(b["conta"]):
            por_valor[(b["conta"], b["centavos"])].append(j)
            por_contraparte[(b["conta"], b["contraparte"])].append(j)

    # 0. Estornos dentro do razão: mesma referência e valores opostos
    for i, a in enumerate(r):
        if i in usados_r or pd.isna(a["ref"]):
            continue
        for j in por_referencia.get((a["conta"], a["ref"]), []):
            if j <= i or j in usados_r:
                continue
            b = r[j]
            if b["centavos"] == -a["centavos"]:
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
        for j in por_valor.get((a["conta"], a["centavos"]), []):
            if j in usados_e:
                continue
            b = e[j]
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
    conciliado_por_chave = {}
    for k, linha in linha_do_extrato.items():
        o = e[k]
        if isinstance(o["texto"], str):
            chave = (o["conta"], o["centavos"], o["data"], o["texto"])
            conciliado_por_chave.setdefault(chave, linha)   # o primeiro conciliado leva a duplicidade
    for j, b in enumerate(e):
        if j in usados_e or not isinstance(b["texto"], str):
            continue
        linha = conciliado_por_chave.get((b["conta"], b["centavos"], b["data"], b["texto"]))
        if linha is not None:
            linha["situacao"] = DUPLICADO
            linha["_ids_extrato"].append(b["id"])
            linha["valor_extrato"] = round(linha["valor_extrato"] + b["valor"], 2)
            usados_e.add(j)

    # 3. Valor divergente: mesma contraparte, mesmo sinal, data próxima, valor parecido
    for i, a in enumerate(r):
        if i in usados_r or a["contraparte"] == "":
            continue
        melhor = None
        for j in por_contraparte.get((a["conta"], a["contraparte"]), []):
            if j in usados_e:
                continue
            b = e[j]
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
