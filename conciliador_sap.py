"""Conciliação bancária: razão contábil (SAP) x extrato bancário.

Ponto de entrada do projeto: reexporta as funções e constantes que ficam em src/.
Todos os dados usados neste projeto são fictícios.

Onde fica cada coisa:
  src/constants.py       situações, tolerâncias e categorias
  src/loaders.py         leitura e padronização das abas do Excel
  src/reconciliation.py  regras de conciliação, nesta ordem:
                           0. estornos no razão (mesma referência, valores opostos)
                           1. valor exato + data dentro da tolerância
                           2. duplicidade no extrato
                           3. valor divergente (mesma contraparte, data próxima)
                           4. pendências (só no razão ou só no extrato)
  src/validators.py      prova de saldo e conferência com o gabarito
  src/reports.py         relatório em Excel
"""
from src.constants import (
    CATEGORIAS_EXTRATO,
    CONCILIADO,
    DATA_DIVERGENTE,
    DEP_TRANSITO,
    DUPLICADO,
    ESTORNADO,
    ESTORNO,
    PAG_TRANSITO,
    SITUACOES_COM_ACAO,
    SITUACOES_SO_RAZAO,
    SO_EXTRATO,
    TOLERANCIA_DIAS,
    TOLERANCIA_VALOR_PCT,
    VALOR_DIVERGENTE,
)
from src.loaders import carregar, contraparte
from src.reconciliation import conciliar
from src.reports import exportar_excel
from src.validators import prova_de_saldo, validar_contra_gabarito

__all__ = [
    "CATEGORIAS_EXTRATO", "CONCILIADO", "DATA_DIVERGENTE", "DEP_TRANSITO", "DUPLICADO",
    "ESTORNADO", "ESTORNO", "PAG_TRANSITO", "SITUACOES_COM_ACAO", "SITUACOES_SO_RAZAO",
    "SO_EXTRATO", "TOLERANCIA_DIAS", "TOLERANCIA_VALOR_PCT", "VALOR_DIVERGENTE",
    "carregar", "conciliar", "contraparte", "exportar_excel", "prova_de_saldo",
    "validar_contra_gabarito",
]
