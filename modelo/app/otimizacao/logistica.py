"""Cálculos geográficos do serviço de otimização.

Todas as distâncias vêm da fórmula de haversine sobre uma esfera de raio médio terrestre.
Internamente o serviço trabalha com **metros inteiros**: o CP-SAT só aceita coeficientes
inteiros, e concentrar o único arredondamento aqui mantém o custo logístico exatamente
reprodutível entre execuções (requisito da Fase 4).

A malha viária real não é considerada — decisão de modelagem registrada em
``docs/arquitetura.md`` e discutida em ``docs/formulacao-matematica.md``.
"""

from __future__ import annotations

import math
from typing import List, NamedTuple, Sequence

RAIO_MEDIO_TERRA_METROS = 6_371_008.8
"""Raio médio terrestre (IUGG), em metros."""

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


def distancia_haversine_metros(origem: Ponto, destino: Ponto) -> int:
    """Distância de grande círculo entre dois pontos, em metros inteiros.

    Args:
        origem: ponto de partida.
        destino: ponto de chegada.

    Returns:
        A distância arredondada para o metro mais próximo (meio para cima).
    """
    latitude_origem = math.radians(origem.latitude)
    latitude_destino = math.radians(destino.latitude)
    delta_latitude = latitude_destino - latitude_origem
    delta_longitude = math.radians(destino.longitude - origem.longitude)

    seno_metade_lat = math.sin(delta_latitude / 2.0)
    seno_metade_lon = math.sin(delta_longitude / 2.0)
    termo = seno_metade_lat**2 + math.cos(latitude_origem) * math.cos(latitude_destino) * (
        seno_metade_lon**2
    )
    angulo = 2.0 * math.asin(min(1.0, math.sqrt(termo)))
    return math.floor(RAIO_MEDIO_TERRA_METROS * angulo + 0.5)


def distancia_ida_volta_metros(origem: Ponto, destino: Ponto) -> int:
    """Distância linearizada de ida e volta entre a origem e um mercado, em metros.

    É o termo ``2 · d(origem, j)`` que entra na função objetivo. Por não depender da ordem
    de visita, mantém o modelo linear e é uma cota superior da rota real.

    Args:
        origem: ponto de partida do usuário.
        destino: localização do mercado.

    Returns:
        O dobro da distância de haversine, em metros inteiros.
    """
    return 2 * distancia_haversine_metros(origem, destino)


def matriz_de_distancias_metros(pontos: Sequence[Ponto]) -> List[List[int]]:
    """Matriz simétrica de distâncias entre todos os pontos informados.

    Usada pela ordenação da rota, onde o índice 0 costuma ser a origem.

    Args:
        pontos: sequência de pontos na ordem em que serão indexados.

    Returns:
        Matriz ``n x n`` de distâncias em metros inteiros, com diagonal nula.
    """
    quantidade = len(pontos)
    matriz = [[0] * quantidade for _ in range(quantidade)]
    for indice_a in range(quantidade):
        for indice_b in range(indice_a + 1, quantidade):
            distancia = distancia_haversine_metros(pontos[indice_a], pontos[indice_b])
            matriz[indice_a][indice_b] = distancia
            matriz[indice_b][indice_a] = distancia
    return matriz


def metros_para_km(metros: int) -> float:
    """Converte metros inteiros em quilômetros para apresentação.

    Args:
        metros: distância em metros inteiros.

    Returns:
        A distância em quilômetros, arredondada para :data:`CASAS_DECIMAIS_KM` casas.
    """
    return round(metros / 1000.0, CASAS_DECIMAIS_KM)
