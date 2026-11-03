from pathlib import Path

import pandas as pd
import pytest

from conciliador_sap import (CONCILIADO, DATA_DIVERGENTE, DEP_TRANSITO, DUPLICADO, ESTORNADO,
                             ESTORNO, SO_EXTRATO, VALOR_DIVERGENTE, carregar, conciliar,
                             contraparte, prova_de_saldo, validar_contra_gabarito)

ARQUIVO = Path("dados/Base_de_dados_-_contas_bancarias.xlsx")


def _razao(*linhas):
    """linhas: (id, data, texto, ref, valor)"""
    df = pd.DataFrame(linhas, columns=["id", "data", "texto", "ref", "valor"])
    df["conta_razao"], df["conta"] = 11010001, "56789-0"
    df["data"] = pd.to_datetime(df["data"])
    df["centavos"] = (df["valor"] * 100).round().astype("int64")
    df["contraparte"] = df["texto"].map(contraparte)
    return df


def _extrato(*linhas):
    """linhas: (id, data, texto, valor)"""
    df = pd.DataFrame(linhas, columns=["id", "data", "texto", "valor"])
    df["conta_razao"], df["conta"] = 11010001, "56789-0"
    df["data"] = pd.to_datetime(df["data"])
    df["centavos"] = (df["valor"] * 100).round().astype("int64")
    df["contraparte"] = df["texto"].map(contraparte)
    return df


def _situacoes(resultado):
    return sorted(resultado["situacao"].tolist())


def test_contraparte_ignora_acento_e_caixa():
    assert contraparte("Pagamento NF 1 - Horizonte Limpeza ME") == contraparte(
        "PIX ENVIADO - HORIZONTE LIMPEZA ME")
    assert contraparte("PAGTO FOLHA PAGAMENTO") == ""


def test_valor_e_data_iguais_concilia():
    r = conciliar(_razao((1, "2026-10-01", "Receb - Zeta SA", "NF1", 100.00)),
                  _extrato((9, "2026-10-01", "PIX - ZETA SA", 100.00)))
    assert _situacoes(r) == [CONCILIADO]


def test_data_diferente_dentro_da_tolerancia():
    r = conciliar(_razao((1, "2026-10-01", "Receb - Zeta SA", "NF1", 100.00)),
                  _extrato((9, "2026-10-03", "PIX - ZETA SA", 100.00)))
    assert _situacoes(r) == [DATA_DIVERGENTE]
    assert r.loc[0, "dias_diferenca"] == 2


def test_data_fora_da_tolerancia_nao_concilia():
    r = conciliar(_razao((1, "2026-10-01", "Receb - Zeta SA", "NF1", 100.00)),
                  _extrato((9, "2026-10-20", "PIX - ZETA SA", 100.00)))
    assert CONCILIADO not in _situacoes(r) and DATA_DIVERGENTE not in _situacoes(r)


def test_duplicidade_no_extrato():
    r = conciliar(_razao((1, "2026-10-08", "Receb - Zeta SA", "NF1", 500.00)),
                  _extrato((9, "2026-10-08", "TED - ZETA SA", 500.00),
                           (10, "2026-10-08", "TED - ZETA SA", 500.00)))
    assert _situacoes(r) == [DUPLICADO]
    assert r.loc[0, "doc_extrato"] == "9 / 10"
    assert r.loc[0, "diferenca"] == -500.00


def test_valor_divergente_mesma_contraparte():
    r = conciliar(_razao((1, "2026-10-09", "Pagto NF 8 - Horizonte Ltda", "NF8", -1000.00)),
                  _extrato((9, "2026-10-09", "PIX - HORIZONTE LTDA", -975.00)))
    assert _situacoes(r) == [VALOR_DIVERGENTE]
    assert r.loc[0, "diferenca"] == -25.00


def test_valor_muito_diferente_nao_e_tratado_como_divergencia():
    r = conciliar(_razao((1, "2026-10-09", "Pagto NF 8 - Horizonte Ltda", "NF8", -1000.00)),
                  _extrato((9, "2026-10-09", "PIX - HORIZONTE LTDA", -400.00)))
    assert VALOR_DIVERGENTE not in _situacoes(r)


def test_estorno_no_razao():
    r = conciliar(_razao((1, "2026-10-08", "Pagto NF 5 - Prime Ltda", "NF5", -700.00),
                         (2, "2026-10-09", "ESTORNO Pagto NF 5 - Prime Ltda", "NF5", 700.00)),
                  _extrato())
    assert _situacoes(r) == sorted([ESTORNADO, ESTORNO])
    assert r["diferenca"].sum() == 0


def test_somente_no_extrato_e_deposito_em_transito():
    r = conciliar(_razao((1, "2026-10-02", "Receb NF 3 - Alfa Ltda", "NF3", 900.00)),
                  _extrato((9, "2026-10-13", "TARIFA COBRANCA BOLETOS", -50.00)))
    assert _situacoes(r) == sorted([DEP_TRANSITO, SO_EXTRATO])
    assert "tarifas" in r.loc[r["situacao"] == SO_EXTRATO, "acao"].iloc[0]


def test_cada_lancamento_do_extrato_concilia_so_uma_vez():
    r = conciliar(_razao((1, "2026-10-01", "Receb - Zeta SA", "NF1", 100.00),
                         (2, "2026-10-01", "Receb - Zeta SA", "NF2", 100.00)),
                  _extrato((9, "2026-10-01", "PIX - ZETA SA", 100.00)))
    assert _situacoes(r) == sorted([CONCILIADO, DEP_TRANSITO])


@pytest.mark.skipif(not ARQUIVO.exists(), reason="base de dados não encontrada")
def test_base_completa_bate_com_o_gabarito_e_a_prova_de_saldo_fecha():
    razao, extrato, contas = carregar(str(ARQUIVO))
    resultado = conciliar(razao, extrato)
    total, acertos, divergencias = validar_contra_gabarito(resultado, str(ARQUIVO))
    assert acertos == total, divergencias.to_string()
    prova = prova_de_saldo(resultado, contas)
    assert (prova["Diferença não explicada"].abs() < 0.005).all()
