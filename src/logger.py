import logging

logger = logging.getLogger("conciliador")


def configurar_logs(nivel: int = logging.INFO) -> None:
    """Define o formato dos logs. Chame uma vez, no ponto de entrada (main.py).

    Fica fora da importação para que quem apenas importa o módulo
    não tenha a configuração de log do seu programa alterada.
    """
    logging.basicConfig(level=nivel, format="%(asctime)s - %(levelname)s - %(message)s")
