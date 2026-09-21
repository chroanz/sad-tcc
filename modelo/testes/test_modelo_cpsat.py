"""Testes da formulação CP-SAT.

Cada cenário tem o ótimo conhecido antes de o solver rodar: ou por cálculo manual do
trade-off entre economia no item e custo da visita extra, ou por uma relação estrutural
que a formulação obriga a valer.
"""

from app.esquemas import MotivoNaoAtendido, StatusOtimizacao
from app.otimizacao.logistica import Ponto, distancia_haversine_metros, distancia_ida_volta_metros
from app.otimizacao.modelo_cpsat import (
    arredondar_meio_para_cima,
    resolver_alocacao_de_compras,
)
from testes.apoio import (
    CENTRO_JUAZEIRO,
    COORDENADAS_MERCADOS,
    mercado_de_cada_item,
    montar_item,
    montar_requisicao,
)

CUSTO_POR_VISITA = 800
CUSTO_POR_KM = 120


def custo_logistico_do_mercado(mercado_id: int) -> int:
    """Custo logístico de visitar um mercado, na mesma conta que o modelo faz.

    Args:
        mercado_id: identificador do mercado no recorte de Juazeiro do Norte.

    Returns:
        Custo em centavos de incluir esse mercado na rota.
    """
    _, latitude, longitude = COORDENADAS_MERCADOS[mercado_id]
    origem = Ponto(CENTRO_JUAZEIRO["latitude"], CENTRO_JUAZEIRO["longitude"])
    metros = distancia_ida_volta_metros(origem, Ponto(latitude, longitude))
    return CUSTO_POR_VISITA + arredondar_meio_para_cima(CUSTO_POR_KM * metros / 1000.0)


def test_concentra_quando_a_economia_nao_paga_a_visita_extra():
    """Economia de R$ 4,00 não cobre a ida ao Limoeiro: tudo no mercado do Centro."""
    economia_no_item = 400
    assert economia_no_item < custo_logistico_do_mercado(5)

    requisicao = montar_requisicao(
        itens=[
            montar_item(1, [(1, 2599), (5, 2599 - economia_no_item)]),
            montar_item(2, [(1, 1899)]),
        ],
        mercados_ids=[1, 5],
    )
    resposta = resolver_alocacao_de_compras(requisicao)

    assert resposta.status == StatusOtimizacao.OTIMO
    assert resposta.quantidade_mercados_visitados == 1
    assert mercado_de_cada_item(resposta) == {1: 1, 2: 1}


def test_visita_o_segundo_mercado_quando_a_economia_compensa():
    """Economia de R$ 70,00 supera com folga o custo da visita extra."""
    economia_no_item = 7000
    assert economia_no_item > custo_logistico_do_mercado(5)

    requisicao = montar_requisicao(
        itens=[
            montar_item(1, [(1, 1899)]),
            montar_item(2, [(1, 9000), (5, 9000 - economia_no_item)]),
        ],
        mercados_ids=[1, 5],
    )
    resposta = resolver_alocacao_de_compras(requisicao)

    assert resposta.quantidade_mercados_visitados == 2
    assert mercado_de_cada_item(resposta) == {1: 1, 2: 5}


def test_visitar_dois_mercados_custa_menos_que_duas_idas_e_voltas_independentes():
    """A correção do modelo: o usuário vai de um mercado ao outro, não volta à origem entre eles.

    Antes desta correção, o custo logístico de visitar dois mercados era exatamente
    ``custo_logistico_do_mercado(1) + custo_logistico_do_mercado(5)`` — a soma de duas idas
    e voltas independentes. Agora é o custo do circuito real origem → um mercado → o outro →
    origem, que a desigualdade triangular garante ser sempre menor ou igual, e estritamente
    menor sempre que os dois mercados não estão alinhados com a origem.
    """
    requisicao = montar_requisicao(
        itens=[montar_item(1, [(1, 1000)]), montar_item(2, [(5, 1000)])],
        mercados_ids=[1, 5],
        peso_conveniencia=0.0,
    )
    resposta = resolver_alocacao_de_compras(requisicao)

    assert resposta.quantidade_mercados_visitados == 2
    soma_das_idas_e_voltas_independentes = custo_logistico_do_mercado(
        1
    ) + custo_logistico_do_mercado(5)
    assert resposta.custo_logistico_centavos < soma_das_idas_e_voltas_independentes

    origem = Ponto(CENTRO_JUAZEIRO["latitude"], CENTRO_JUAZEIRO["longitude"])
    _, latitude_1, longitude_1 = COORDENADAS_MERCADOS[1]
    _, latitude_5, longitude_5 = COORDENADAS_MERCADOS[5]
    ponto_1 = Ponto(latitude_1, longitude_1)
    ponto_5 = Ponto(latitude_5, longitude_5)
    distancia_real_circuito_km = (
        distancia_haversine_metros(origem, ponto_1)
        + distancia_haversine_metros(ponto_1, ponto_5)
        + distancia_haversine_metros(ponto_5, origem)
    ) / 1000.0
    assert resposta.distancia_total_km == round(distancia_real_circuito_km, 3)


def test_perfil_economico_ignora_a_logistica():
    """Com peso 0 o termo logístico some e vale a pena buscar qualquer centavo."""
    requisicao = montar_requisicao(
        itens=[
            montar_item(1, [(1, 1899)]),
            montar_item(2, [(1, 2599), (5, 2499)]),
        ],
        mercados_ids=[1, 5],
        peso_conveniencia=0.0,
    )
    resposta = resolver_alocacao_de_compras(requisicao)

    assert mercado_de_cada_item(resposta)[2] == 5
    assert resposta.custo_itens_centavos == 1899 + 2499


def test_perfil_conveniente_concentra_mais_que_o_economico():
    """O mesmo cenário resolvido com peso alto usa menos mercados."""
    itens = [
        montar_item(1, [(1, 5000), (3, 3000)]),
        montar_item(2, [(1, 5000), (4, 3000)]),
        montar_item(3, [(1, 4000)]),
    ]
    economico = resolver_alocacao_de_compras(
        montar_requisicao(itens, mercados_ids=[1, 3, 4], peso_conveniencia=0.0)
    )
    conveniente = resolver_alocacao_de_compras(
        montar_requisicao(itens, mercados_ids=[1, 3, 4], peso_conveniencia=10.0)
    )

    assert economico.quantidade_mercados_visitados > conveniente.quantidade_mercados_visitados
    assert conveniente.quantidade_mercados_visitados == 1
    assert economico.custo_itens_centavos < conveniente.custo_itens_centavos


def test_item_sem_nenhum_preco_cadastrado_vira_nao_atendido():
    requisicao = montar_requisicao(
        itens=[montar_item(1, [(1, 1899)]), montar_item(2, [])],
        mercados_ids=[1],
    )
    resposta = resolver_alocacao_de_compras(requisicao)

    assert len(resposta.itens_nao_atendidos) == 1
    assert resposta.itens_nao_atendidos[0].item_id == 2
    assert resposta.itens_nao_atendidos[0].motivo == MotivoNaoAtendido.SEM_CANDIDATO


def test_estoque_insuficiente_desqualifica_o_candidato():
    """Há preço nos dois mercados, mas nenhum tem as 10 unidades pedidas."""
    requisicao = montar_requisicao(
        itens=[
            montar_item(
                1,
                [(1, 1899), (5, 1799)],
                quantidade=10.0,
                estoques={1: 3.0, 5: 2.0},
            )
        ],
        mercados_ids=[1, 5],
    )
    resposta = resolver_alocacao_de_compras(requisicao)

    assert resposta.compras_por_mercado == []
    assert resposta.itens_nao_atendidos[0].motivo == MotivoNaoAtendido.SEM_CANDIDATO_COM_ESTOQUE


def test_estoque_exatamente_igual_a_quantidade_e_elegivel():
    """A restrição é estoque maior ou igual à quantidade, não estritamente maior."""
    requisicao = montar_requisicao(
        itens=[montar_item(1, [(1, 1899)], quantidade=4.0, estoques={1: 4.0})],
        mercados_ids=[1],
    )
    resposta = resolver_alocacao_de_compras(requisicao)

    assert resposta.itens_nao_atendidos == []
    assert mercado_de_cada_item(resposta) == {1: 1}


def test_lista_vazia_devolve_custos_zerados():
    resposta = resolver_alocacao_de_compras(montar_requisicao(itens=[], mercados_ids=[1, 2]))

    assert resposta.custo_total_centavos == 0
    assert resposta.custo_itens_centavos == 0
    assert resposta.custo_logistico_centavos == 0
    assert resposta.quantidade_mercados_visitados == 0
    assert resposta.compras_por_mercado == []
    assert resposta.rota == []


def test_mercado_unico_recebe_tudo_que_tem_oferta():
    requisicao = montar_requisicao(
        itens=[montar_item(1, [(3, 1899)]), montar_item(2, [(3, 2599)]), montar_item(3, [])],
        mercados_ids=[3],
    )
    resposta = resolver_alocacao_de_compras(requisicao)

    assert resposta.quantidade_mercados_visitados == 1
    assert mercado_de_cada_item(resposta) == {1: 3, 2: 3}
    assert [item.item_id for item in resposta.itens_nao_atendidos] == [3]


def test_nenhum_item_atendivel_nao_levanta_excecao():
    requisicao = montar_requisicao(
        itens=[montar_item(1, []), montar_item(2, [])], mercados_ids=[1, 2]
    )
    resposta = resolver_alocacao_de_compras(requisicao)

    assert resposta.compras_por_mercado == []
    assert len(resposta.itens_nao_atendidos) == 2
    assert resposta.custo_total_centavos == 0


def test_desempate_escolhe_a_solucao_com_menos_mercados():
    """Preços iguais e peso 0: sem a segunda fase, a escolha seria arbitrária."""
    requisicao = montar_requisicao(
        itens=[montar_item(1, [(1, 1000)]), montar_item(2, [(1, 1000), (5, 1000)])],
        mercados_ids=[1, 5],
        peso_conveniencia=0.0,
    )
    resposta = resolver_alocacao_de_compras(requisicao)

    assert resposta.quantidade_mercados_visitados == 1
    assert mercado_de_cada_item(resposta) == {1: 1, 2: 1}


def test_mesma_entrada_produz_exatamente_a_mesma_saida():
    itens = [
        montar_item(1, [(1, 2599), (3, 2450), (5, 2300)]),
        montar_item(2, [(1, 1899), (4, 1750)]),
        montar_item(3, [(3, 990), (5, 950)]),
    ]
    primeira = resolver_alocacao_de_compras(montar_requisicao(itens, [1, 3, 4, 5]))
    segunda = resolver_alocacao_de_compras(montar_requisicao(itens, [1, 3, 4, 5]))

    assert primeira.model_dump(exclude={"diagnostico"}) == segunda.model_dump(
        exclude={"diagnostico"}
    )


def test_custo_total_e_a_soma_das_parcelas():
    requisicao = montar_requisicao(
        itens=[montar_item(1, [(1, 2599)]), montar_item(2, [(5, 900)])],
        mercados_ids=[1, 5],
    )
    resposta = resolver_alocacao_de_compras(requisicao)

    assert (
        resposta.custo_total_centavos
        == resposta.custo_itens_centavos + resposta.custo_logistico_centavos
    )
    soma_subtotais = sum(compra.subtotal_centavos for compra in resposta.compras_por_mercado)
    assert soma_subtotais == resposta.custo_itens_centavos


def test_custo_logistico_reportado_nao_embute_o_peso():
    """O custo logístico devolvido é o gasto real; o peso só afeta a decisão."""
    itens = [montar_item(1, [(1, 2599)])]
    com_peso_um = resolver_alocacao_de_compras(montar_requisicao(itens, [1], peso_conveniencia=1.0))
    com_peso_tres = resolver_alocacao_de_compras(
        montar_requisicao(itens, [1], peso_conveniencia=3.0)
    )

    assert com_peso_um.custo_logistico_centavos == com_peso_tres.custo_logistico_centavos
    assert com_peso_um.custo_logistico_centavos == custo_logistico_do_mercado(1)


def test_quantidade_fracionaria_arredonda_meio_para_cima():
    """1,5 vezes R$ 3,33 resulta em R$ 4,995, que arredonda para R$ 5,00."""
    requisicao = montar_requisicao(
        itens=[montar_item(1, [(1, 333)], quantidade=1.5)], mercados_ids=[1]
    )
    resposta = resolver_alocacao_de_compras(requisicao)

    assert resposta.custo_itens_centavos == 500


def test_rota_visita_cada_mercado_escolhido_uma_unica_vez():
    requisicao = montar_requisicao(
        itens=[
            montar_item(1, [(1, 9000), (3, 1000)]),
            montar_item(2, [(1, 9000), (4, 1000)]),
            montar_item(3, [(1, 500)]),
        ],
        mercados_ids=[1, 3, 4],
        peso_conveniencia=0.0,
    )
    resposta = resolver_alocacao_de_compras(requisicao)

    identificadores_da_rota = [parada.mercado_id for parada in resposta.rota]
    identificadores_das_compras = [compra.mercado_id for compra in resposta.compras_por_mercado]
    assert sorted(identificadores_da_rota) == sorted(identificadores_das_compras)
    assert len(set(identificadores_da_rota)) == len(identificadores_da_rota)
    assert [parada.ordem for parada in resposta.rota] == list(range(1, len(resposta.rota) + 1))
