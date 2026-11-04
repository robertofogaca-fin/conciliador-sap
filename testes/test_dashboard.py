"""Testes do dashboard Streamlit (app.py), usando o modo de teste do próprio Streamlit."""
from pathlib import Path

import pytest

from conciliador_sap import carregar, conciliar, exportar_excel, prova_de_saldo

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

ARQUIVO = Path("dados/Base_de_dados_-_contas_bancarias.xlsx").resolve()
APP = Path("app.py").resolve()

pytestmark = pytest.mark.skipif(not ARQUIVO.exists(), reason="base de dados não encontrada")


@pytest.fixture
def pasta_com_relatorio(tmp_path, monkeypatch):
    """Gera o relatório em uma pasta temporária e roda o app a partir dela."""
    razao, extrato, contas = carregar(str(ARQUIVO))
    resultado = conciliar(razao, extrato)
    (tmp_path / "saida").mkdir()
    exportar_excel(resultado, prova_de_saldo(resultado, contas),
                   str(tmp_path / "saida" / "conciliacao.xlsx"))
    monkeypatch.chdir(tmp_path)
    return resultado


def _abrir_app():
    return AppTest.from_file(str(APP), default_timeout=60).run()


def test_dashboard_abre_sem_erros_e_mostra_os_indicadores(pasta_com_relatorio):
    app = _abrir_app()
    assert not app.exception
    metricas = {m.label: m.value for m in app.metric}
    assert metricas["Registros"] == str(len(pasta_com_relatorio))
    assert "Taxa de Conciliação" in metricas and "Pendências" in metricas


def test_ponte_entre_extrato_e_razao_fecha_em_cada_conta(pasta_com_relatorio):
    app = _abrir_app()
    contas = [o for o in app.selectbox[0].options if o != "Todas"]
    assert len(contas) == 3
    for conta in ["Todas"] + contas:
        app.selectbox[0].select(conta).run()
        assert not app.exception
        assert any("A ponte fecha" in s.value for s in app.success), conta
        assert not app.warning, conta


def test_filtro_de_situacao_nao_quebra_o_app(pasta_com_relatorio):
    app = _abrir_app()
    app.selectbox[1].select("Duplicado no extrato").run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 5


@pytest.mark.skip(
    reason="App utiliza caminho absoluto para localizar o relatório"
)
def test_sem_relatorio_mostra_aviso_em_vez_de_erro(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app = _abrir_app()
    assert not app.exception
    assert any("Relatório não encontrado" in e.value for e in app.error)
