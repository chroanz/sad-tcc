"""Ordenação da rota de visita, executada **depois** do solve.

O modelo CP-SAT decide *quais* mercados visitar usando a distância linearizada de ida e
volta, que não depende da ordem. A ordem de visita é um problema de caixeiro-viajante
sobre o subconjunto já escolhido, resolvido aqui de forma isolada: manter a ordenação
dentro do MILP transformaria a formulação em um TSP com seleção, fora do escopo da PoC
(ver ``docs/arquitetura.md``).

Estratégia:

* até :data:`LIMITE_ENUMERACAO_EXATA` mercados (o teto da PoC), enumeração **exata** de
  todas as permutações — 8! = 40320 sequências, custo desprezível e ótimo garantido;
* acima disso, heurística vizinho mais próximo seguida de refinamento 2-opt.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import List, NamedTuple, Sequence, Tuple

from app.otimizacao.logistica import Ponto, matriz_de_distancias_metros

LIMITE_ENUMERACAO_EXATA = 8
"""Número máximo de mercados para os quais a rota é resolvida por enumeração exata."""


class MercadoParaRota(NamedTuple):
    """Mercado escolhido pela otimização, pronto para entrar na rota.

    Attributes:
        mercado_id: identificador do mercado.
        nome: nome exibido ao usuário.
        ponto: localização do mercado.
    """

    mercado_id: int
    nome: str
    ponto: Ponto


@dataclass(frozen=True)
class ParadaOrdenada:
    """Parada da rota já posicionada na sequência de visita.

    Attributes:
        mercado_id: identificador do mercado visitado.
        nome: nome do mercado.
        distancia_do_anterior_metros: distância desde a parada anterior (ou a origem).
    """

    mercado_id: int
    nome: str
    distancia_do_anterior_metros: int


@dataclass(frozen=True)
class RotaCalculada:
    """Resultado da ordenação da rota.

    Attributes:
        paradas: mercados na ordem sugerida de visita.
        distancia_total_metros: distância real do circuito origem → paradas → origem.
        metodo: ``"enumeracao_exata"`` ou ``"vizinho_mais_proximo_2opt"``.
    """

    paradas: List[ParadaOrdenada]
    distancia_total_metros: int
    metodo: str


def _custo_do_circuito(sequencia: Sequence[int], matriz: List[List[int]]) -> int:
    """Soma das distâncias do circuito origem → sequência → origem.

    Args:
        sequencia: índices dos mercados na matriz (a origem é o índice 0).
        matriz: matriz de distâncias em metros.

    Returns:
        A distância total do circuito, em metros.
    """
    if not sequencia:
        return 0
    total = matriz[0][sequencia[0]]
    for anterior, atual in zip(sequencia, sequencia[1:], strict=False):
        total += matriz[anterior][atual]
    return total + matriz[sequencia[-1]][0]


def _resolver_por_enumeracao(
    quantidade: int, matriz: List[List[int]], identificadores: Sequence[int]
) -> List[int]:
    """Enumera todas as permutações e devolve a melhor sequência de índices.

    O desempate é determinístico: entre circuitos de mesma distância, vence o que tiver a
    menor sequência de ``mercado_id`` em ordem lexicográfica.

    Args:
        quantidade: número de mercados a ordenar.
        matriz: matriz de distâncias, com a origem no índice 0.
        identificadores: ``mercado_id`` de cada índice de mercado, usado no desempate.

    Returns:
        A sequência ótima de índices de mercado.
    """
    melhor_sequencia: Tuple[int, ...] = tuple(range(1, quantidade + 1))
    melhor_chave = (
        _custo_do_circuito(melhor_sequencia, matriz),
        tuple(identificadores[indice - 1] for indice in melhor_sequencia),
    )
    for sequencia in permutations(range(1, quantidade + 1)):
        chave = (
            _custo_do_circuito(sequencia, matriz),
            tuple(identificadores[indice - 1] for indice in sequencia),
        )
        if chave < melhor_chave:
            melhor_chave = chave
            melhor_sequencia = sequencia
    return list(melhor_sequencia)


def _resolver_por_heuristica(quantidade: int, matriz: List[List[int]]) -> List[int]:
    """Constrói a rota pelo vizinho mais próximo e refina com 2-opt.

    O critério de desempate na construção é o menor índice, o que torna a heurística
    determinística para uma mesma entrada.

    Args:
        quantidade: número de mercados a ordenar.
        matriz: matriz de distâncias, com a origem no índice 0.

    Returns:
        A sequência de índices de mercado após o refinamento.
    """
    pendentes = set(range(1, quantidade + 1))
    sequencia: List[int] = []
    atual = 0
    while pendentes:
        proximo = min(pendentes, key=lambda indice: (matriz[atual][indice], indice))
        sequencia.append(proximo)
        pendentes.remove(proximo)
        atual = proximo

    melhorou = True
    while melhorou:
        melhorou = False
        for inicio in range(len(sequencia) - 1):
            for fim in range(inicio + 1, len(sequencia)):
                candidata = (
                    sequencia[:inicio] + sequencia[inicio : fim + 1][::-1] + sequencia[fim + 1 :]
                )
                if _custo_do_circuito(candidata, matriz) < _custo_do_circuito(sequencia, matriz):
                    sequencia = candidata
                    melhorou = True
    return sequencia


def ordenar_rota(origem: Ponto, mercados: Sequence[MercadoParaRota]) -> RotaCalculada:
    """Ordena os mercados escolhidos partindo da origem e retornando a ela.

    Args:
        origem: ponto de partida e de retorno do usuário.
        mercados: mercados selecionados pelo modelo, em qualquer ordem.

    Returns:
        A rota com as paradas na ordem sugerida, a distância desde a parada anterior de
        cada uma e a distância total real do circuito.
    """
    if not mercados:
        return RotaCalculada(paradas=[], distancia_total_metros=0, metodo="rota_vazia")

    pontos = [origem] + [mercado.ponto for mercado in mercados]
    matriz = matriz_de_distancias_metros(pontos)
    identificadores = [mercado.mercado_id for mercado in mercados]

    if len(mercados) <= LIMITE_ENUMERACAO_EXATA:
        sequencia = _resolver_por_enumeracao(len(mercados), matriz, identificadores)
        metodo = "enumeracao_exata"
    else:
        sequencia = _resolver_por_heuristica(len(mercados), matriz)
        metodo = "vizinho_mais_proximo_2opt"

    paradas: List[ParadaOrdenada] = []
    anterior = 0
    for indice in sequencia:
        mercado = mercados[indice - 1]
        paradas.append(
            ParadaOrdenada(
                mercado_id=mercado.mercado_id,
                nome=mercado.nome,
                distancia_do_anterior_metros=matriz[anterior][indice],
            )
        )
        anterior = indice

    return RotaCalculada(
        paradas=paradas,
        distancia_total_metros=_custo_do_circuito(sequencia, matriz),
        metodo=metodo,
    )
