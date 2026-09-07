"""Testes do baseline de economia.

O baseline responde à pergunta "quanto eu economizo em relação a comprar tudo num
mercado só?". A regra do contrato tem dois níveis, e é a distinção entre eles que estes
testes protegem: comparar a recomendação com um mercado que atende menos itens
superestimaria a economia.
"""

from app.otimizacao.modelo_cpsat import resolver_alocacao_de_compras
from testes.apoio import montar_item, montar_requisicao


def test_comparacao_completa_quando_um_mercado_atende_a_lista_toda():
    """Cada mercado é barato num item e caro no outro: dividir bate qualquer um sozinho."""
    requisicao = montar_requisicao(
        itens=[
            montar_item(1, [(1, 1000), (5, 9000)]),
            montar_item(2, [(1, 9000), (5, 1000)]),
        ],
        mercados_ids=[1, 5],
        peso_conveniencia=0.0,
    )
    resposta = resolver_alocacao_de_compras(requisicao)

    assert resposta.quantidade_mercados_visitados == 2
    assert resposta.economia.comparacao_parcial is False
    assert resposta.economia.itens_comparados == 2
    assert resposta.economia.observacao is None
    assert resposta.economia.economia_centavos > 0
    assert resposta.economia.custo_mercado_unico_centavos > resposta.custo_total_centavos


def test_economia_e_a_diferenca_entre_baseline_e_recomendacao():
    """Na comparação completa os dois lados cobrem a lista inteira."""
    requisicao = montar_requisicao(
        itens=[
            montar_item(1, [(1, 1000), (5, 9000)]),
            montar_item(2, [(1, 9000), (5, 1000)]),
        ],
        mercados_ids=[1, 5],
        peso_conveniencia=0.0,
    )
    resposta = resolver_alocacao_de_compras(requisicao)
    economia = resposta.economia

    assert (
        economia.economia_centavos
        == economia.custo_mercado_unico_centavos - resposta.custo_total_centavos
    )
    assert economia.economia_percentual == round(
        100.0 * economia.economia_centavos / economia.custo_mercado_unico_centavos, 2
    )


def test_baseline_inclui_a_parcela_logistica_dos_dois_lados():
    """Um único mercado também custa uma visita: a régua tem de ser a mesma."""
    requisicao = montar_requisicao(
        itens=[montar_item(1, [(1, 5000)])],
        mercados_ids=[1],
    )
    resposta = resolver_alocacao_de_compras(requisicao)

    assert resposta.economia.custo_mercado_unico_centavos == resposta.custo_total_centavos
    assert resposta.economia.economia_centavos == 0


def test_comparacao_parcial_quando_nenhum_mercado_cobre_a_lista_inteira():
    """Cada mercado tem só metade da lista: a comparação encolhe e se declara parcial."""
    requisicao = montar_requisicao(
        itens=[
            montar_item(1, [(1, 1000)]),
            montar_item(2, [(1, 1000)]),
            montar_item(3, [(5, 1000)]),
        ],
        mercados_ids=[1, 5],
        peso_conveniencia=0.0,
    )
    resposta = resolver_alocacao_de_compras(requisicao)

    assert resposta.economia.comparacao_parcial is True
    assert resposta.economia.itens_comparados == 2
    assert resposta.economia.mercado_unico_id == 1
    assert resposta.economia.observacao is not None


def test_sem_itens_atendidos_a_economia_nao_e_inventada():
    requisicao = montar_requisicao(
        itens=[montar_item(1, []), montar_item(2, [])], mercados_ids=[1, 5]
    )
    economia = resolver_alocacao_de_compras(requisicao).economia

    assert economia.mercado_unico_id is None
    assert economia.custo_mercado_unico_centavos is None
    assert economia.economia_centavos is None
    assert economia.economia_percentual is None
    assert economia.observacao is not None


def test_lista_vazia_tambem_devolve_economia_nula_com_observacao():
    economia = resolver_alocacao_de_compras(montar_requisicao([], [1, 5])).economia

    assert economia.economia_centavos is None
    assert economia.itens_comparados == 0
    assert economia.observacao is not None


def test_baseline_escolhe_o_mercado_completo_mais_barato():
    """Dois mercados cobrem tudo; o baseline tem de ser o mais barato dos dois."""
    requisicao = montar_requisicao(
        itens=[montar_item(1, [(1, 8000), (3, 5000)]), montar_item(2, [(1, 8000), (3, 5000)])],
        mercados_ids=[1, 3],
        peso_conveniencia=0.0,
    )
    resposta = resolver_alocacao_de_compras(requisicao)

    assert resposta.economia.comparacao_parcial is False
    assert resposta.economia.mercado_unico_id == 3
