"""Baseline de mercado único — a resposta à pergunta "quanto eu economizei?".

A comparação segue a seção *Baseline de economia* de ``docs/contrato-otimizacao.md`` e tem
dois níveis, para nunca comparar conjuntos diferentes de itens:

1. **Completa** — existe pelo menos um mercado capaz de atender sozinho todos os itens que
   a solução atendeu; o baseline é o mais barato entre eles.
2. **Parcial** — nenhum mercado atende a lista inteira; o baseline passa a ser o de maior
   cobertura (desempate pelo menor custo) e os dois lados são recalculados apenas sobre os
   itens que esse mercado cobre.

Nos dois níveis o baseline carrega a mesma parcela logística da recomendação (custo de
visita mais ida e volta), de modo que os dois lados sejam medidos com a mesma régua.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from app.esquemas import Economia


@dataclass(frozen=True)
class ItemParaEconomia:
    """Item atendido pela recomendação, com todos os seus custos alternativos.

    Attributes:
        item_id: identificador do item na lista.
        mercado_escolhido: mercado ao qual o modelo alocou o item.
        custo_escolhido_centavos: custo pago no mercado escolhido.
        custo_por_mercado_centavos: custo do item em cada mercado que o cobre, ou seja,
            que tem preço cadastrado **e** estoque suficiente.
    """

    item_id: int
    mercado_escolhido: int
    custo_escolhido_centavos: int
    custo_por_mercado_centavos: Dict[int, int] = field(default_factory=dict)


def _economia_indisponivel(observacao: str) -> Economia:
    """Monta o resultado usado quando não existe base de comparação.

    Args:
        observacao: texto que explica ao usuário por que não há economia calculada.

    Returns:
        Um :class:`~app.esquemas.Economia` com todos os campos monetários nulos.
    """
    return Economia(
        mercado_unico_id=None,
        mercado_unico_nome=None,
        custo_mercado_unico_centavos=None,
        economia_centavos=None,
        economia_percentual=None,
        itens_comparados=0,
        comparacao_parcial=False,
        observacao=observacao,
    )


def calcular_economia(
    itens_atendidos: Sequence[ItemParaEconomia],
    custo_logistico_por_mercado_centavos: Dict[int, int],
    nomes_de_mercado: Dict[int, str],
) -> Economia:
    """Compara o custo da recomendação com o do melhor mercado único.

    Args:
        itens_atendidos: itens que a solução conseguiu alocar, com seus custos alternativos.
        custo_logistico_por_mercado_centavos: custo de visitar um mercado isoladamente
            (``custo_por_visita + custo_por_km · 2 · d(origem, j)``), já em centavos.
        nomes_de_mercado: nome de cada ``mercado_id``, para compor a resposta.

    Returns:
        O bloco ``economia`` do contrato, com o nível de comparação usado e, quando ela é
        parcial ou impossível, a ``observacao`` que explica a limitação.
    """
    if not itens_atendidos:
        return _economia_indisponivel(
            "Nenhum item foi atendido; nao ha base de comparacao com mercado unico."
        )

    cobertura: Dict[int, List[ItemParaEconomia]] = {}
    for mercado_id in custo_logistico_por_mercado_centavos:
        cobertos = [
            item for item in itens_atendidos if mercado_id in item.custo_por_mercado_centavos
        ]
        if cobertos:
            cobertura[mercado_id] = cobertos

    if not cobertura:
        return _economia_indisponivel(
            "Nenhum mercado cobre sozinho sequer um dos itens atendidos; "
            "a economia nao pode ser estimada."
        )

    total_atendido = len(itens_atendidos)
    completos = [
        mercado_id for mercado_id, cobertos in cobertura.items() if len(cobertos) == total_atendido
    ]

    if completos:
        mercado_baseline = min(
            completos,
            key=lambda mercado_id: (
                _custo_do_baseline(
                    cobertura[mercado_id], mercado_id, custo_logistico_por_mercado_centavos
                ),
                mercado_id,
            ),
        )
        comparacao_parcial = False
        observacao: Optional[str] = None
    else:
        maior_cobertura = max(len(cobertos) for cobertos in cobertura.values())
        empatados = [
            mercado_id
            for mercado_id, cobertos in cobertura.items()
            if len(cobertos) == maior_cobertura
        ]
        mercado_baseline = min(
            empatados,
            key=lambda mercado_id: (
                _custo_do_baseline(
                    cobertura[mercado_id], mercado_id, custo_logistico_por_mercado_centavos
                ),
                mercado_id,
            ),
        )
        comparacao_parcial = True
        observacao = (
            f"Nenhum mercado atende sozinho os {total_atendido} itens da recomendacao. "
            f"A comparacao usa o mercado de maior cobertura "
            f"({nomes_de_mercado.get(mercado_baseline, '')}) "
            f"e considera apenas os {maior_cobertura} itens que ele cobre."
        )

    subconjunto = cobertura[mercado_baseline]
    custo_baseline = _custo_do_baseline(
        subconjunto, mercado_baseline, custo_logistico_por_mercado_centavos
    )
    custo_recomendacao = _custo_da_recomendacao(subconjunto, custo_logistico_por_mercado_centavos)
    economia_centavos = custo_baseline - custo_recomendacao
    percentual = round(100.0 * economia_centavos / custo_baseline, 2) if custo_baseline else 0.0

    return Economia(
        mercado_unico_id=mercado_baseline,
        mercado_unico_nome=nomes_de_mercado.get(mercado_baseline),
        custo_mercado_unico_centavos=custo_baseline,
        economia_centavos=economia_centavos,
        economia_percentual=percentual,
        itens_comparados=len(subconjunto),
        comparacao_parcial=comparacao_parcial,
        observacao=observacao,
    )


def _custo_do_baseline(
    itens: Sequence[ItemParaEconomia],
    mercado_id: int,
    custo_logistico_por_mercado_centavos: Dict[int, int],
) -> int:
    """Custo de comprar o subconjunto inteiro em um único mercado.

    Args:
        itens: itens cobertos pelo mercado.
        mercado_id: mercado usado como baseline.
        custo_logistico_por_mercado_centavos: custo de uma visita isolada a cada mercado.

    Returns:
        A soma dos itens naquele mercado mais a parcela logística de uma única visita.
    """
    total_itens = sum(item.custo_por_mercado_centavos[mercado_id] for item in itens)
    return total_itens + custo_logistico_por_mercado_centavos.get(mercado_id, 0)


def _custo_da_recomendacao(
    itens: Sequence[ItemParaEconomia],
    custo_logistico_por_mercado_centavos: Dict[int, int],
) -> int:
    """Custo do lado da recomendação, restrito ao mesmo subconjunto de itens.

    A parcela logística considera apenas os mercados que a recomendação usa **para esses
    itens** — é o que torna a comparação parcial honesta: se um mercado só existe na
    solução por causa de um item fora do subconjunto, seu custo não entra na conta.

    Args:
        itens: subconjunto comparado.
        custo_logistico_por_mercado_centavos: custo de uma visita isolada a cada mercado.

    Returns:
        A soma dos custos escolhidos mais a logística dos mercados envolvidos.
    """
    total_itens = sum(item.custo_escolhido_centavos for item in itens)
    mercados_usados = {item.mercado_escolhido for item in itens}
    total_logistico = sum(
        custo_logistico_por_mercado_centavos.get(mercado_id, 0) for mercado_id in mercados_usados
    )
    return total_itens + total_logistico
