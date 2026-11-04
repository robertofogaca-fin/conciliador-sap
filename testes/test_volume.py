"""Testes com dados sintéticos em volume: nenhum lançamento pode se perder ou se repetir."""
import random

import pandas as pd
import pytest

from conciliador_sap import conciliar, contraparte

CONTAS = {11010001: "56789-0", 11010002: "123456-7", 11010003: "98765-4"}
NOMES = ["Alfa Comércio Ltda", "Beta Distribuidora SA", "Delta Tecnologia ME",
         "Sigma Logística Ltda", "Titan Manutenção SA", "Zeta Farmacêutica SA"]
VALORES_REPETIDOS = [10000, -25000, 100000]   # centavos; geram empates de propósito


def gerar_base(n: int, seed: int = 1):
    """Gera n lançamentos no razão e o extrato correspondente, com os problemas típicos."""
    rnd = random.Random(seed)
    inicio = pd.Timestamp("2026-10-01")
    razao, extrato = [], []
    id_extrato = 480000

    def add_extrato(conta_razao, data, texto, centavos):
        nonlocal id_extrato
        id_extrato += 1
        extrato.append({"id": id_extrato, "conta_razao": conta_razao, "conta": CONTAS[conta_razao],
                        "data": data, "texto": texto, "valor": centavos / 100, "centavos": centavos,
                        "contraparte": contraparte(texto)})

    for k in range(n):
        conta_razao = rnd.choice(list(CONTAS))
        nome = rnd.choice(NOMES)
        centavos = rnd.randint(-900000, 900000) or 1
        if rnd.random() < 0.15:
            centavos = rnd.choice(VALORES_REPETIDOS)
        data = inicio + pd.Timedelta(days=rnd.randint(0, 29))
        texto = f"Pagamento NF {k} - {nome}"
        razao.append({"id": 1400000000 + k, "conta_razao": conta_razao, "conta": CONTAS[conta_razao],
                      "data": data, "texto": texto, "ref": f"NF{k}", "valor": centavos / 100,
                      "centavos": centavos, "contraparte": contraparte(texto)})

        sorteio = rnd.random()
        historico = f"PIX - {nome.upper()}"
        data_banco = data + pd.Timedelta(days=rnd.randint(0, 4))
        if sorteio < 0.70:                                   # bate (às vezes com data diferente)
            add_extrato(conta_razao, data_banco, historico, centavos)
        elif sorteio < 0.78:                                 # valor divergente (~2%)
            add_extrato(conta_razao, data_banco, historico, round(centavos * 1.02))
        elif sorteio < 0.84:                                 # duplicado no extrato
            add_extrato(conta_razao, data, historico, centavos)
            add_extrato(conta_razao, data, historico, centavos)
        elif sorteio < 0.88:                                 # lançamento e estorno no razão
            razao.append({"id": 1400000000 + n + k, "conta_razao": conta_razao,
                          "conta": CONTAS[conta_razao], "data": data + pd.Timedelta(days=1),
                          "texto": f"ESTORNO {texto}", "ref": f"NF{k}", "valor": -centavos / 100,
                          "centavos": -centavos, "contraparte": contraparte(texto)})
        # o resto fica só no razão (em trânsito)
        if rnd.random() < 0.05:                              # tarifa só no extrato
            add_extrato(conta_razao, data, "TARIFA COBRANCA BOLETOS", -rnd.randint(1000, 20000))

    return pd.DataFrame(razao), pd.DataFrame(extrato)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_nenhum_lancamento_se_perde_ou_se_repete(seed):
    razao, extrato = gerar_base(600, seed)
    resultado = conciliar(razao, extrato)

    docs_razao = resultado["doc_razao"].dropna().astype(int).tolist()
    assert sorted(docs_razao) == sorted(razao["id"].tolist())

    docs_extrato = [int(x) for texto in resultado["doc_extrato"] if texto for x in texto.split(" / ")]
    assert sorted(docs_extrato) == sorted(extrato["id"].tolist())


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_diferenca_de_saldo_fecha(seed):
    razao, extrato = gerar_base(600, seed)
    resultado = conciliar(razao, extrato)
    esperado = round(razao["valor"].sum() - extrato["valor"].sum(), 2)
    assert round(resultado["diferenca"].sum(), 2) == pytest.approx(esperado, abs=0.005)
