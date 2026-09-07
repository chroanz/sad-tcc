"""Configuração do serviço de otimização, lida de variáveis de ambiente ``MODELO_*``.

O serviço é stateless: a configuração define apenas valores padrão de parâmetros que a
requisição pode sobrescrever (custos logísticos e limite de tempo), o teto de instância da
PoC e os parâmetros de reprodutibilidade do solver.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from app import VERSAO


def _inteiro_do_ambiente(nome: str, padrao: int) -> int:
    """Lê uma variável de ambiente inteira, caindo no padrão quando ausente ou inválida.

    Args:
        nome: nome da variável de ambiente.
        padrao: valor usado quando a variável não existe ou não é um inteiro válido.

    Returns:
        O inteiro configurado.
    """
    bruto = os.getenv(nome)
    if bruto is None or bruto.strip() == "":
        return padrao
    try:
        return int(bruto)
    except ValueError:
        return padrao


def _decimal_do_ambiente(nome: str, padrao: float) -> float:
    """Lê uma variável de ambiente de ponto flutuante, caindo no padrão quando inválida.

    Args:
        nome: nome da variável de ambiente.
        padrao: valor usado quando a variável não existe ou não é um número válido.

    Returns:
        O valor decimal configurado.
    """
    bruto = os.getenv(nome)
    if bruto is None or bruto.strip() == "":
        return padrao
    try:
        return float(bruto)
    except ValueError:
        return padrao


@dataclass(frozen=True)
class Configuracao:
    """Parâmetros globais do serviço.

    Attributes:
        porta: porta HTTP do uvicorn (usada apenas pelo entrypoint local).
        limite_tempo_segundos: teto de tempo padrão de cada fase do solve.
        custo_por_visita_centavos: custo fixo padrão atribuído a cada mercado visitado.
        custo_por_km_centavos: custo padrão atribuído a cada quilômetro percorrido.
        maximo_itens: teto de itens por instância (RNF03).
        maximo_mercados: teto de mercados por instância (RNF03).
        semente_solver: semente fixa do CP-SAT, exigida pela reprodutibilidade da Fase 4.
        versao: versão do serviço, devolvida em ``GET /saude``.
    """

    porta: int
    limite_tempo_segundos: float
    custo_por_visita_centavos: int
    custo_por_km_centavos: int
    maximo_itens: int
    maximo_mercados: int
    semente_solver: int
    versao: str


def carregar_configuracao() -> Configuracao:
    """Monta a configuração a partir do ambiente.

    Returns:
        A instância de :class:`Configuracao` com os valores vigentes.
    """
    return Configuracao(
        porta=_inteiro_do_ambiente("MODELO_PORTA", 8001),
        limite_tempo_segundos=_decimal_do_ambiente("MODELO_LIMITE_TEMPO_SEGUNDOS", 10.0),
        custo_por_visita_centavos=_inteiro_do_ambiente("MODELO_CUSTO_POR_VISITA_CENTAVOS", 800),
        custo_por_km_centavos=_inteiro_do_ambiente("MODELO_CUSTO_POR_KM_CENTAVOS", 120),
        maximo_itens=_inteiro_do_ambiente("MODELO_MAXIMO_ITENS", 20),
        maximo_mercados=_inteiro_do_ambiente("MODELO_MAXIMO_MERCADOS", 8),
        semente_solver=_inteiro_do_ambiente("MODELO_SEMENTE_SOLVER", 42),
        versao=os.getenv("MODELO_VERSAO", VERSAO),
    )


CONFIGURACAO = carregar_configuracao()
"""Configuração carregada uma única vez na importação do módulo."""
