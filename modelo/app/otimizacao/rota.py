"""Ordem de visita dos mercados escolhidos: o mais próximo primeiro.

O modelo CP-SAT decide **quais** mercados visitar (por preço e disponibilidade); este
módulo decide **em que ordem**. A rota é um único percurso: o usuário sai da origem uma vez,
vai de mercado em mercado e só volta para a origem no fim — nunca uma ida e volta
independente por mercado.

A ordem segue a regra do **vizinho mais próximo**: a partir do ponto atual (começando pela
origem), a próxima parada é sempre o mercado ainda não visitado mais próximo. É o critério
que as pessoas usam na prática ao "fazer a feira", e por isso é o que a recomendação
reproduz. Não é um Caixeiro-Viajante: como a distância não é precificada, não há por que
otimizar o percurso — só apresentá-lo numa ordem natural.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

from app.otimizacao.logistica import Ponto, distancia_em_linha_reta_metros


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
        paradas: mercados na ordem de visita.
        distancia_total_metros: distância do percurso origem → paradas → origem,
            informativa (não entra no objetivo).
    """

    paradas: List[ParadaOrdenada]
    distancia_total_metros: int


def ordenar_pelo_mais_proximo(
    origem: Ponto, mercados: Sequence[Tuple[int, str, Ponto]]
) -> RotaCalculada:
    """Ordena os mercados visitados pela regra do vizinho mais próximo.

    Args:
        origem: ponto de partida e de retorno do usuário.
        mercados: ``(mercado_id, nome, ponto)`` de cada mercado a visitar, em qualquer ordem.

    Returns:
        A rota com as paradas em ordem e a distância total do percurso fechado. Empates de
        distância são resolvidos pelo menor ``mercado_id``, para que a saída seja
        determinística.
    """
    pendentes = list(mercados)
    paradas: List[ParadaOrdenada] = []
    distancia_total = 0
    atual = origem

    while pendentes:
        proximo = min(
            pendentes,
            key=lambda mercado: (distancia_em_linha_reta_metros(atual, mercado[2]), mercado[0]),
        )
        pendentes.remove(proximo)
        mercado_id, nome, ponto = proximo
        distancia = distancia_em_linha_reta_metros(atual, ponto)
        distancia_total += distancia
        paradas.append(
            ParadaOrdenada(
                mercado_id=mercado_id,
                nome=nome,
                distancia_do_anterior_metros=distancia,
            )
        )
        atual = ponto

    if paradas:
        distancia_total += distancia_em_linha_reta_metros(atual, origem)

    return RotaCalculada(paradas=paradas, distancia_total_metros=distancia_total)
