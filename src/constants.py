TOLERANCIA_DIAS = 5          # diferença máxima de datas para considerar o mesmo evento
TOLERANCIA_VALOR_PCT = 0.10  # diferença máxima de valor para sugerir "valor divergente"

CONCILIADO = "Conciliado"
DATA_DIVERGENTE = "Conciliado - data divergente"
DUPLICADO = "Duplicado no extrato"
VALOR_DIVERGENTE = "Valor divergente"
SO_EXTRATO = "Somente no extrato (não lançado no razão)"
DEP_TRANSITO = "Somente no razão - depósito em trânsito"
PAG_TRANSITO = "Somente no razão - pagamento em trânsito"
ESTORNADO = "Somente no razão - lançamento estornado"
ESTORNO = "Somente no razão - estorno do lançamento"

SITUACOES_SO_RAZAO = [DEP_TRANSITO, PAG_TRANSITO, ESTORNADO, ESTORNO]
# Situações que exigem alguma providência (vão para a aba Pendencias do Excel)
SITUACOES_COM_ACAO = [DUPLICADO, VALOR_DIVERGENTE, SO_EXTRATO, DEP_TRANSITO, PAG_TRANSITO]

CATEGORIAS_EXTRATO = [
    ("TARIFA", "Despesa bancária - tarifas"),
    ("IOF", "Despesa bancária - IOF"),
    ("RENDIMENTO", "Receita financeira - rendimento de aplicação"),
]
