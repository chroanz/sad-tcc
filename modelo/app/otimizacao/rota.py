"""Extração da ordem de visita a partir do circuito resolvido pelo CP-SAT.

Até uma versão anterior deste módulo, a ordem de visita era um Caixeiro-Viajante resolvido
**depois** do solve, sobre o subconjunto de mercados já escolhido (por enumeração exata ou
heurística). Isso foi abandonado: a escolha de quais mercados visitar dependia de uma
aproximação (ida e volta independente por mercado) que não conhecia a rota real, e por
`docs/formulacao-matematica.md` §7 esse descolamento chegava a superestimar o custo
logístico em mais de 60% em instâncias com vários mercados.

Agora o próprio modelo CP-SAT decide *e* ordena a rota na mesma resolução, através da
restrição de circuito (`CpModel.AddCircuit`, em `modelo_cpsat.py`). Este módulo só percorre
os arcos ativos da solução, a partir da origem (nó 0), e monta a lista de paradas — não há
mais busca aqui, só leitura do resultado.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple


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
    """Resultado da extração da rota.

    Attributes:
        paradas: mercados na ordem de visita decidida pelo circuito.
        distancia_total_metros: distância real do circuito origem → paradas → origem.
    """

    paradas: List[ParadaOrdenada]
    distancia_total_metros: int


def extrair_rota(
    proximo_no: Dict[int, int],
    matriz_metros: Sequence[Sequence[int]],
    mercados_por_indice: Dict[int, Tuple[int, str]],
) -> RotaCalculada:
    """Segue os arcos ativos do circuito a partir da origem e monta as paradas em ordem.

    Args:
        proximo_no: para cada índice de nó com arco de saída ativo no circuito resolvido,
            o índice do próximo nó visitado. O nó ``0`` é a origem; não aparece como chave
            quando nenhum mercado foi visitado (circuito vazio).
        matriz_metros: matriz de distâncias em metros, indexada como o circuito (``0`` é a
            origem, os demais índices seguem ``mercados_por_indice``).
        mercados_por_indice: índice do nó (``>= 1``) → ``(mercado_id, nome)``.

    Returns:
        A rota com as paradas na ordem do circuito e a distância total real do trajeto
        origem → paradas → origem.
    """
    if 0 not in proximo_no:
        return RotaCalculada(paradas=[], distancia_total_metros=0)

    paradas: List[ParadaOrdenada] = []
    distancia_total = 0
    anterior = 0
    atual = proximo_no[0]
    while atual != 0:
        mercado_id, nome = mercados_por_indice[atual]
        distancia = matriz_metros[anterior][atual]
        distancia_total += distancia
        paradas.append(
            ParadaOrdenada(
                mercado_id=mercado_id,
                nome=nome,
                distancia_do_anterior_metros=distancia,
            )
        )
        anterior = atual
        atual = proximo_no[atual]
    distancia_total += matriz_metros[anterior][0]

    return RotaCalculada(paradas=paradas, distancia_total_metros=distancia_total)
