from pathlib import Path

from conciliador_sap import (carregar, conciliar, exportar_excel, prova_de_saldo,
                             validar_contra_gabarito)

ARQUIVO = "dados/Base_de_dados_-_contas_bancarias.xlsx"

razao, extrato, contas = carregar(ARQUIVO)
resultado = conciliar(razao, extrato)
prova = prova_de_saldo(resultado, contas)

print("=== RESUMO POR SITUAÇÃO ===")
print(resultado["situacao"].value_counts().to_string())

print("\n=== PROVA DE SALDO ===")
print(prova.T.to_string(header=False, float_format=lambda x: f"{x:,.2f}"))

# A aba Gabarito é usada só para conferir o resultado, nunca na lógica
total, acertos, divergencias = validar_contra_gabarito(resultado, ARQUIVO)
print(f"\nConferência com o gabarito: {acertos} de {total} linhas corretas")
if not divergencias.empty:
    print(divergencias.to_string(index=False))

Path("saida").mkdir(exist_ok=True)
exportar_excel(resultado, prova, "saida/conciliacao.xlsx")
print("\nRelatório gravado em saida/conciliacao.xlsx")
