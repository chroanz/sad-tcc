"""Construtores de instâncias para os testes.

Concentra a montagem de payloads aqui para que cada teste declare apenas o que é
relevante ao cenário que exercita. A origem é o centro de Juazeiro do Norte/CE e os
mercados são supermercados do catálogo, todos dentro da cidade.
"""

from typing import Dict, List, Optional, Sequence, Tuple

from app.esquemas import RequisicaoOtimizacao

CENTRO_JUAZEIRO: Dict[str, float] = {"latitude": -7.2131, "longitude": -39.3153}

# Supermercados do catálogo (004_catalogo_dieese.sql), do mais próximo ao mais distante do
# centro de Juazeiro do Norte.
COORDENADAS_MERCADOS: Dict[int, Tuple[str, float, float]] = {
    1: ("Supermercado Brasília", -7.213100, -39.308032),
    2: ("Supermercado Cuiabá", -7.229162, -39.313879),
    3: ("Supermercado Rio de Janeiro", -7.225936, -39.294961),
    4: ("Supermercado Vitória", -7.237883, -39.328274),
    5: ("Supermercado Palmas", -7.252914, -39.320500),
    6: ("Supermercado Macaé", -7.163770, -39.336109),
}


def montar_mercado(mercado_id: int) -> Dict[str, object]:
    """Devolve o dicionário de um mercado de teste.

    Args:
        mercado_id: identificador entre 1 e 6.

    Returns:
        O mercado no formato do contrato.
    """
    nome, latitude, longitude = COORDENADAS_MERCADOS[mercado_id]
    return {
        "mercado_id": mercado_id,
        "nome": nome,
        "latitude": latitude,
        "longitude": longitude,
    }


def montar_item(
    item_id: int,
    ofertas: Sequence[Tuple[int, int]],
    quantidade: float = 1.0,
    estoques: Optional[Dict[int, float]] = None,
    descricao: Optional[str] = None,
) -> Dict[str, object]:
    """Monta um item com seus candidatos.

    Args:
        item_id: identificador do item.
        ofertas: pares ``(mercado_id, preco_unitario_centavos)``.
        quantidade: quantidade pedida.
        estoques: estoque por mercado; o padrão é folgado (999).
        descricao: rótulo do item.

    Returns:
        O item no formato do contrato.
    """
    disponibilidade = estoques or {}
    candidatos = [
        {
            "mercado_id": mercado_id,
            "marca_id": 100 + item_id,
            "marca_nome": "Marca do item %d" % item_id,
            "preco_unitario_centavos": preco,
            "quantidade_disponivel": disponibilidade.get(mercado_id, 999.0),
        }
        for mercado_id, preco in ofertas
    ]
    return {
        "item_id": item_id,
        "descricao": descricao or ("Item %d" % item_id),
        "quantidade": quantidade,
        "unidade": "un",
        "candidatos": candidatos,
    }


def montar_requisicao(
    itens: List[Dict[str, object]],
    mercados_ids: Sequence[int],
    peso_conveniencia: float = 1.0,
    custo_por_visita_centavos: int = 800,
) -> RequisicaoOtimizacao:
    """Monta a requisição completa já validada pelo Pydantic.

    Args:
        itens: itens montados por :func:`montar_item`.
        mercados_ids: identificadores dos mercados considerados.
        peso_conveniencia: peso da escalarização.
        custo_por_visita_centavos: custo fixo por mercado visitado.

    Returns:
        A requisição pronta para :func:`app.otimizacao.modelo_cpsat.resolver_alocacao_de_compras`.
    """
    return RequisicaoOtimizacao(
        origem=CENTRO_JUAZEIRO,
        peso_conveniencia=peso_conveniencia,
        custo_por_visita_centavos=custo_por_visita_centavos,
        mercados=[montar_mercado(identificador) for identificador in mercados_ids],
        itens=itens,
    )


def mercado_de_cada_item(resposta) -> Dict[int, int]:
    """Extrai o mapa ``item_id -> mercado_id`` de uma resposta.

    Args:
        resposta: resposta devolvida pelo otimizador.

    Returns:
        Dicionário com o mercado escolhido para cada item atendido.
    """
    escolhas: Dict[int, int] = {}
    for compra in resposta.compras_por_mercado:
        for item in compra.itens:
            escolhas[item.item_id] = compra.mercado_id
    return escolhas
