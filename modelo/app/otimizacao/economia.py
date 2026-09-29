"""Baseline de mercado único — a resposta à pergunta "quanto eu economizei?".

A comparação segue a seção *Baseline de economia* de ``docs/contrato-otimizacao.md`` e tem
dois níveis, para nunca comparar conjuntos diferentes de itens:

1. **Completa** — existe pelo menos um mercado capaz de atender sozinho todos os itens que
   a solução atendeu; o baseline é o mais barato entre eles.
2. **Parcial** — nenhum mercado atende a lista inteira; o baseline passa a ser o de maior
   cobertura (desempate pelo menor custo) e os dois lados são recalculados apenas sobre os
   itens que esse mercado cobre.

Nos dois níveis a comparação é **só do que se paga no caixa**: a soma dos itens. O custo
das paradas, que existe só para o modelo pesar conveniência, fica de fora — ninguém o paga
no mercado. O esforço entra à parte, em quilômetros: a resposta traz a distância de ida e
volta até o mercado único, para ser comparada com o percurso da recomendação.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

from app.esquemas import Economia
from app.otimizacao.logistica import metros_para_km


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
    mercados_ids: Iterable[int],
    metros_ida_volta: Dict[int, int],
    nomes_de_mercado: Dict[int, str],
) -> Economia:
    """Compara o que se paga no caixa na recomendação e no melhor mercado único.

    Args:
        itens_atendidos: itens que a solução conseguiu alocar, com seus custos alternativos.
        mercados_ids: todos os mercados da instância, candidatos a baseline.
        metros_ida_volta: distância de ida e volta entre a origem e cada mercado, em
            metros — o percurso de quem compra tudo num mercado só.
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
    for mercado_id in mercados_ids:
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

    def custo_do_baseline(mercado_id: int) -> int:
        return sum(item.custo_por_mercado_centavos[mercado_id] for item in cobertura[mercado_id])

    total_atendido = len(itens_atendidos)
    completos = [
        mercado_id for mercado_id, cobertos in cobertura.items() if len(cobertos) == total_atendido
    ]

    if completos:
        candidatos = completos
        comparacao_parcial = False
    else:
        maior_cobertura = max(len(cobertos) for cobertos in cobertura.values())
        candidatos = [
            mercado_id
            for mercado_id, cobertos in cobertura.items()
            if len(cobertos) == maior_cobertura
        ]
        comparacao_parcial = True

    mercado_baseline = min(
        candidatos, key=lambda mercado_id: (custo_do_baseline(mercado_id), mercado_id)
    )
    subconjunto = cobertura[mercado_baseline]

    observacao: Optional[str] = None
    if comparacao_parcial:
        observacao = (
            f"Nenhum mercado atende sozinho os {total_atendido} itens da recomendacao. "
            f"A comparacao usa o mercado de maior cobertura "
            f"({nomes_de_mercado.get(mercado_baseline, '')}) "
            f"e considera apenas os {len(subconjunto)} itens que ele cobre."
        )

    custo_baseline = custo_do_baseline(mercado_baseline)
    custo_recomendacao = sum(item.custo_escolhido_centavos for item in subconjunto)
    economia_centavos = custo_baseline - custo_recomendacao
    percentual = round(100.0 * economia_centavos / custo_baseline, 2) if custo_baseline else 0.0

    return Economia(
        mercado_unico_id=mercado_baseline,
        mercado_unico_nome=nomes_de_mercado.get(mercado_baseline),
        custo_mercado_unico_centavos=custo_baseline,
        distancia_mercado_unico_km=(
            metros_para_km(metros_ida_volta[mercado_baseline])
            if mercado_baseline in metros_ida_volta
            else None
        ),
        economia_centavos=economia_centavos,
        economia_percentual=percentual,
        itens_comparados=len(subconjunto),
        comparacao_parcial=comparacao_parcial,
        observacao=observacao,
    )
