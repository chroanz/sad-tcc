"""Testes da extração de rota a partir de um circuito já resolvido."""

from app.otimizacao.rota import extrair_rota


def test_circuito_vazio_nao_tem_paradas():
    rota = extrair_rota(proximo_no={}, matriz_metros=[[0]], mercados_por_indice={})

    assert rota.paradas == []
    assert rota.distancia_total_metros == 0


def test_uma_parada_e_ida_e_volta():
    matriz = [
        [0, 100],
        [100, 0],
    ]
    rota = extrair_rota(
        proximo_no={0: 1, 1: 0},
        matriz_metros=matriz,
        mercados_por_indice={1: (7, "Mercado A")},
    )

    assert [parada.mercado_id for parada in rota.paradas] == [7]
    assert rota.paradas[0].distancia_do_anterior_metros == 100
    assert rota.distancia_total_metros == 200


def test_segue_a_ordem_do_circuito_ate_voltar_a_origem():
    matriz = [
        [0, 10, 20],
        [10, 0, 5],
        [20, 5, 0],
    ]
    rota = extrair_rota(
        proximo_no={0: 2, 2: 1, 1: 0},
        matriz_metros=matriz,
        mercados_por_indice={1: (11, "Mercado B"), 2: (12, "Mercado C")},
    )

    assert [parada.mercado_id for parada in rota.paradas] == [12, 11]
    assert [parada.distancia_do_anterior_metros for parada in rota.paradas] == [20, 5]
    assert rota.distancia_total_metros == 20 + 5 + 10
