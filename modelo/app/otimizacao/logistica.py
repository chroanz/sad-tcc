"""Cálculos geográficos do serviço de otimização.

A distância entre dois pontos é a **linha reta** em um plano local: as diferenças de
latitude e de longitude viram metros (a longitude encolhida pelo cosseno da latitude
média) e o resultado é a hipotenusa. É a forma mais simples de distância que ainda fala
em metros, suficiente para a PoC — a malha viária real não é considerada.

A distância **não entra na função objetivo**: o SAD decide por preço e disponibilidade, e
precificar o deslocamento está fora do escopo. Ela serve apenas para o recorte por raio,
para ordenar a visita (ver ``rota.py``) e para informar ao usuário o tamanho do percurso.

Internamente o serviço trabalha com **metros inteiros**, e concentrar o único arredondamento
aqui mantém os valores exatamente reprodutíveis entre execuções (requisito da Fase 4).
"""

from __future__ import annotations

import math
from typing import NamedTuple

RAIO_MEDIO_TERRA_METROS = 6_371_008.8
"""Raio médio terrestre (IUGG), em metros — converte graus em metros."""

CASAS_DECIMAIS_KM = 3
"""Precisão de apresentação das distâncias em quilômetros (equivale a 1 metro)."""


class Ponto(NamedTuple):
    """Par de coordenadas em graus decimais.

    Attributes:
        latitude: latitude em graus, no intervalo [-90, 90].
        longitude: longitude em graus, no intervalo [-180, 180].
    """

    latitude: float
    longitude: float


def distancia_em_linha_reta_metros(origem: Ponto, destino: Ponto) -> int:
    """Distância em linha reta entre dois pontos, em metros inteiros.

    ``dy = Δlatitude · R`` e ``dx = Δlongitude · cos(latitude média) · R``, com os ângulos
    em radianos; a distância é ``√(dx² + dy²)``.

    Args:
        origem: ponto de partida.
        destino: ponto de chegada.

    Returns:
        A distância arredondada para o metro mais próximo (meio para cima).
    """
    latitude_media = math.radians((origem.latitude + destino.latitude) / 2.0)
    dy = math.radians(destino.latitude - origem.latitude) * RAIO_MEDIO_TERRA_METROS
    dx = (
        math.radians(destino.longitude - origem.longitude)
        * math.cos(latitude_media)
        * RAIO_MEDIO_TERRA_METROS
    )
    return math.floor(math.hypot(dx, dy) + 0.5)


def metros_para_km(metros: int) -> float:
    """Converte metros inteiros em quilômetros para apresentação.

    Args:
        metros: distância em metros inteiros.

    Returns:
        A distância em quilômetros, arredondada para :data:`CASAS_DECIMAIS_KM` casas.
    """
    return round(metros / 1000.0, CASAS_DECIMAIS_KM)
