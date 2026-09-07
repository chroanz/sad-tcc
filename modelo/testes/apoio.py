"""Construtores de instâncias para os testes.

Concentra a montagem de payloads aqui para que cada teste declare apenas o que é
relevante ao cenário que exercita. As coordenadas seguem o recorte real do trabalho:
Juazeiro do Norte/CE.
"""

from typing import Dict, List, Optional, Sequence, Tuple

from app.esquemas import RequisicaoOtimizacao

CENTRO_JUAZEIRO: Dict[str, float] = {"latitude": -7.2131, "longitude": -39.3153}

# Mercados reais do recorte, do mais próximo ao mais distante do centro.
COORDENADAS_MERCADOS: Dict[int, Tuple[str, float, float]] = {
    1: ("Mercado Central do Juazeiro", -7.214500, -39.316800),
    2: ("Supermercado Bom Preço Triângulo", -7.204200, -39.320500),
    3: ("Supermercado Vila Nova Salesianos", -7.220800, -39.304200),
    4: ("Hipermercado Lagoa Seca", -7.235000, -39.330000),
    5: ("Atacadão do Limoeiro", -7.247000, -39.346000),
    6: ("Supermercado Economia Muriti", -7.264000, -39.279000),
}


def montar_mercado(mercado_id: int) -> Dict[str, object]:
    """Devolve o dicionário de um mercado do recorte de Juazeiro do Norte.

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
    custo_por_km_centavos: int = 120,
) -> RequisicaoOtimizacao:
    """Monta a requisição completa já validada pelo Pydantic.

    Args:
        itens: itens montados por :func:`montar_item`.
        mercados_ids: identificadores dos mercados considerados.
        peso_conveniencia: peso da escalarização.
        custo_por_visita_centavos: custo fixo por mercado visitado.
        custo_por_km_centavos: custo por quilômetro percorrido.

    Returns:
        A requisição pronta para :func:`app.otimizacao.modelo_cpsat.resolver_alocacao_de_compras`.
    """
    return RequisicaoOtimizacao(
        origem=CENTRO_JUAZEIRO,
        peso_conveniencia=peso_conveniencia,
        custo_por_visita_centavos=custo_por_visita_centavos,
        custo_por_km_centavos=custo_por_km_centavos,
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
