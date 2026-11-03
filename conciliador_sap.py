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

from src.reconciliation import conciliar
# ----------------------------------------------------------- prova de saldo
from src.validators import (
    prova_de_saldo,
    validar_contra_gabarito,
)


# ---------------------------------------------------------------- validação

from src.validators import (
    prova_de_saldo,
    validar_contra_gabarito,
)



from src.reports import exportar_excel
