# Conciliador Bancário: Razão SAP x Extrato

![Testes](https://github.com/robertofogaca-fin/conciliador-sap/actions/workflows/testes.yml/badge.svg)

Script em Python que concilia o razão contábil (extrato de contas SAP) com o extrato bancário
de várias contas correntes, classifica cada diferença e comprova que a soma das pendências
explica a diferença de saldo. Os resultados podem ser explorados em um dashboard Streamlit.

> Todos os dados deste repositório são fictícios.

## O que mudou em relação à primeira versão

| Primeira versão | Esta versão |
|---|---|
| Valor + data, uma conta | Várias contas, com mapa conta do razão ↔ conta corrente |
| Três listas (conciliados, só extrato, só razão) | Oito situações classificadas (veja abaixo) |
| Sem prova de saldo | Prova de saldo por conta: diferença explicada pelas pendências |
| Saída em CSV | Relatório em Excel (Resumo, Prova_Saldo, Detalhe, Pendencias) |
| Sem interface | Dashboard em Streamlit com a ponte entre extrato e razão |
| Dados de exemplo mínimos | Base com 91 lançamentos no razão e 96 no extrato |

## Regras de conciliação (nesta ordem)

0. **Estornos no razão:** lançamento e estorno com a mesma referência e valores opostos.
1. **Valor exato + data dentro da tolerância** (padrão: 5 dias). Se há mais de um candidato,
   prefere o de mesma contraparte e, depois, o de data mais próxima.
2. **Duplicidade no extrato:** item com mesmo valor, data e histórico de um já conciliado.
3. **Valor divergente:** mesma contraparte, mesmo sinal, data próxima e valor até 10% diferente.
4. **Pendências:** o que sobrou é depósito/pagamento em trânsito (só no razão) ou
   lançamento não registrado (só no extrato), com sugestão de categoria (tarifa, IOF, rendimento).

A contraparte é extraída do texto: o nome depois do último " - ", sem acento e em maiúsculas.
Os valores são comparados em centavos (inteiros), para evitar erros de arredondamento.

## Estrutura do projeto

```
.
├── app.py                  # dashboard Streamlit
├── main.py                 # executa a conciliação e gera o relatório
├── conciliador_sap.py      # ponto de entrada: reexporta as funções de src/
├── src/
│   ├── constants.py        # situações, tolerâncias e categorias
│   ├── loaders.py          # leitura e padronização das abas do Excel
│   ├── reconciliation.py   # regras de conciliação
│   ├── validators.py       # prova de saldo e conferência com o gabarito
│   ├── reports.py          # relatório em Excel
│   └── logger.py           # logger do projeto e configuração do formato (chamada no main.py)
├── dados/                  # base de exemplo (fictícia)
├── saida/                  # relatório gerado (não versionado)
├── testes/
│   ├── test_conciliador_sap.py  # regras de conciliação e conferência com o gabarito
│   ├── test_volume.py           # dados sintéticos em volume: nada se perde, saldo fecha
│   └── test_dashboard.py        # dashboard Streamlit (modo de teste do próprio Streamlit)
├── .github/workflows/testes.yml # roda o pytest a cada push
├── pytest.ini              # configura o pytest (pasta de testes e caminho de importação)
├── requirements.txt        # dependências do projeto
└── requirements-dev.txt    # inclui as dependências de teste
```

## Como rodar

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python main.py
pytest
streamlit run app.py
```

O `main.py` grava o relatório em `saida/conciliacao.xlsx`, e o dashboard lê esse arquivo.
Por isso, rode o `main.py` antes de abrir o dashboard.

## Dashboard

- **Prova de saldo:** gráfico em cascata que parte do saldo final do extrato, soma as pendências
  (só no razão, só no extrato, duplicidades e divergências) e chega ao saldo final do razão.
  Um aviso confirma quando a diferença está totalmente explicada.
- **Indicadores:** taxa de conciliação (linhas "Conciliado" e "Conciliado - data divergente"
  sobre o total de linhas do detalhe), número de registros e de pendências.
- **Detalhamento:** tabela filtrável por situação e por conta corrente.

## Resultado com a base de exemplo

| Situação | Itens |
|---|---|
| Conciliado | 64 |
| Conciliado - data divergente | 7 |
| Duplicado no extrato | 5 |
| Valor divergente | 3 |
| Somente no extrato (não lançado no razão) | 12 |
| Somente no razão - depósito em trânsito | 8 |
| Somente no razão - lançamento estornado / estorno | 2 / 2 |

Prova de saldo (R$):

| Conta do razão | Diferença razão - extrato | Só no razão | Só no extrato | Duplicidades | Divergências | Não explicada |
|---|---|---|---|---|---|---|
| 11010001 | 76.541,90 | 101.459,69 | -167,84 | -24.749,95 | 0,00 | 0,00 |
| 11010002 | 85.615,94 | 54.848,89 | -110,93 | 31.270,95 | -392,97 | 0,00 |
| 11010003 | 9.251,25 | 122.444,98 | -100,32 | -113.319,36 | 225,95 | 0,00 |

## Validação

A base traz uma aba `Gabarito` com a situação esperada de cada item. Ela é usada **somente
para conferir** o resultado (`validar_contra_gabarito`), nunca na lógica de conciliação.
O resultado atual bate em 103 de 103 linhas. Os testes automatizados (`pytest`) cobrem:

- cada regra de conciliação, com casos pequenos;
- a base completa contra o gabarito, com a prova de saldo fechando;
- bases sintéticas maiores, conferindo que nenhum lançamento se perde nem se repete;
- o dashboard, incluindo a troca de conta, o filtro de situação e a ausência do relatório.

## Limitações

- A tolerância de 5 dias foi escolhida olhando a base de exemplo (a maior diferença de data
  nela é de 5 dias). Em dados reais, ajuste `TOLERANCIA_DIAS` ao prazo de compensação de
  cada meio de pagamento.
- Casar com o gabarito em uma base fictícia não prova o mesmo desempenho em dados reais.
- Não faz conciliação 1 para N (um depósito do banco que agrupa vários lançamentos).
- Uma conta corrente é identificada só pelo número; em dados reais, use banco + agência + conta.
- Itens "em trânsito" são classificados por exclusão (estão no razão e não no extrato do período).
- A busca usa índices por conta, valor, contraparte e referência. Em um teste local com dados
  sintéticos de cerca de 6 mil linhas no razão, a conciliação levou menos de 1 segundo; ainda assim,
  não foi testada com volumes muito maiores.
- O dashboard lê o relatório já gerado em `saida/`, que não é versionado, então ele precisa
  do `main.py` rodado localmente antes.

## Próximos passos

- Conciliação 1 para N (adquirência, liquidação agrupada)
- Similaridade de texto para desempatar valores repetidos
- Leitura de extratos em OFX e CSV de bancos reais
- Executar a conciliação dentro do dashboard, para publicá-lo online sem depender de `saida/`
