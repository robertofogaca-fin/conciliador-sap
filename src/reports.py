def exportar_excel(resultado: pd.DataFrame, prova: pd.DataFrame, caminho: str) -> None:
    """Grava o relatório em Excel: Resumo, Prova_Saldo, Detalhe e Pendencias."""
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    detalhe = resultado.rename(columns=COLUNAS_DETALHE)[list(COLUNAS_DETALHE.values())]
    pendencias = detalhe[detalhe["Situação"].isin(SITUACOES_COM_ACAO)]
    resumo = pd.crosstab(resultado["situacao"], resultado["conta_razao"],
                         margins=True, margins_name="Total")
    resumo.index.name = "Situação"
    resumo.columns = [str(c) for c in resumo.columns]

    with pd.ExcelWriter(caminho, engine="openpyxl") as xl:
        resumo.to_excel(xl, sheet_name="Resumo")
        prova.to_excel(xl, sheet_name="Prova_Saldo", index=False)
        detalhe.to_excel(xl, sheet_name="Detalhe", index=False)
        pendencias.to_excel(xl, sheet_name="Pendencias", index=False)

        cabecalho = PatternFill("solid", start_color="1F3864")
        for ws in xl.book.worksheets:
            for celula in ws[1]:
                celula.font = Font(name="Arial", bold=True, color="FFFFFF", size=10)
                celula.fill = cabecalho
                celula.alignment = Alignment(wrap_text=True, vertical="center")
            titulos = [c.value for c in ws[1]]
            for linha in ws.iter_rows(min_row=2):
                for celula, titulo in zip(linha, titulos):
                    celula.font = Font(name="Arial", size=10)
                    t = str(titulo)
                    if t.startswith(("Valor", "Diferença (", "Saldo", "Só no", "Duplicidades",
                                     "Valores", "Diferença não")):
                        celula.number_format = "#,##0.00;(#,##0.00);-"
                    elif t.startswith("Data"):
                        celula.number_format = "dd/mm/yyyy"
            for i, titulo in enumerate(titulos, start=1):
                largura = max(len(str(titulo)), *(len(str(c.value or "")) for c in ws[get_column_letter(i)]))
                ws.column_dimensions[get_column_letter(i)].width = min(largura + 2, 60)
            ws.freeze_panes = "A2"
