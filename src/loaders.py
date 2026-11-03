import unicodedata

import pandas as pd


def contraparte(texto) -> str:
    """Extrai o nome do cliente/fornecedor: o que vem depois do último ' - '.

    'Pagamento NF 8579 - Horizonte Limpeza ME' e
    'PIX ENVIADO - HORIZONTE LIMPEZA ME' dão o mesmo resultado.
    """
    partes = str(texto).split(" - ")
    if len(partes) < 2:
        return ""
    sem_acento = unicodedata.normalize("NFKD", partes[-1])
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.upper().strip()


def _centavos(valores: pd.Series) -> pd.Series:
    # Trabalhar em centavos (inteiros) evita erros de arredondamento
    return (valores * 100).round().astype("int64")


def carregar(caminho: str):
    """Lê as abas Contas, Razao_SAP e Extrato_Bancario e padroniza as colunas."""
    contas = pd.read_excel(caminho, sheet_name="Contas", dtype={"Conta corrente": str})
    razao = pd.read_excel(caminho, sheet_name="Razao_SAP")
    extrato = pd.read_excel(caminho, sheet_name="Extrato_Bancario", dtype={"Conta": str})

    conta_corrente = dict(zip(contas["Conta do Razão"], contas["Conta corrente"]))
    conta_razao = {v: k for k, v in conta_corrente.items()}

    r = pd.DataFrame({
        "id": razao["Nº Documento"].astype("int64"),
        "conta_razao": razao["Conta do Razão"],
        "conta": razao["Conta do Razão"].map(conta_corrente),
        "data": razao["Data Lançamento"],
        "texto": razao["Texto"],
        "ref": razao["Referência"],
        "valor": razao["Montante ML"],
    })
    r["centavos"] = _centavos(r["valor"])
    r["contraparte"] = r["texto"].map(contraparte)

    e = pd.DataFrame({
        "id": extrato["Nº Documento"].astype("int64"),
        "conta_razao": extrato["Conta"].map(conta_razao),
        "conta": extrato["Conta"],
        "data": extrato["Data Movimento"],
        "texto": extrato["Histórico"],
        "valor": extrato["Valor"],
    })
    e["centavos"] = _centavos(e["valor"])
    e["contraparte"] = e["texto"].map(contraparte)

    return r, e, contas