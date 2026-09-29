"""Testes da ordem de visita: o mais próximo primeiro, num único percurso."""

from app.otimizacao.logistica import Ponto
from app.otimizacao.rota import ordenar_pelo_mais_proximo

ORIGEM = Ponto(0.0, 0.0)
# Pontos no equador, a leste da origem: 1°, 2° e 3° de longitude (~111 km cada grau).
PERTO = (10, "Perto", Ponto(0.0, 1.0))
MEIO = (20, "Meio", Ponto(0.0, 2.0))
LONGE = (30, "Longe", Ponto(0.0, 3.0))


def test_sem_mercados_nao_ha_percurso():
    rota = ordenar_pelo_mais_proximo(ORIGEM, [])

    assert rota.paradas == []
    assert rota.distancia_total_metros == 0


def test_uma_parada_e_ida_e_volta():
    rota = ordenar_pelo_mais_proximo(ORIGEM, [PERTO])

    assert [parada.mercado_id for parada in rota.paradas] == [10]
    ida = rota.paradas[0].distancia_do_anterior_metros
    assert rota.distancia_total_metros == 2 * ida


def test_visita_do_mais_proximo_ao_mais_distante_independente_da_ordem_de_entrada():
    rota = ordenar_pelo_mais_proximo(ORIGEM, [LONGE, PERTO, MEIO])

    assert [parada.mercado_id for parada in rota.paradas] == [10, 20, 30]


def test_proxima_parada_e_a_mais_proxima_do_ponto_atual_e_nao_da_origem():
    """Depois do primeiro mercado, a referência passa a ser onde o usuário está."""
    primeiro = (1, "A", Ponto(0.0, 1.0))
    # B fica mais perto da origem que C, mas C fica mais perto de A.
    b = (2, "B", Ponto(-1.2, 0.0))
    c = (3, "C", Ponto(0.0, 2.1))
    rota = ordenar_pelo_mais_proximo(ORIGEM, [b, c, primeiro])

    assert [parada.mercado_id for parada in rota.paradas] == [1, 3, 2]


def test_percurso_volta_para_a_origem_so_no_fim():
    rota = ordenar_pelo_mais_proximo(ORIGEM, [PERTO, MEIO, LONGE])

    trechos = [parada.distancia_do_anterior_metros for parada in rota.paradas]
    volta = rota.distancia_total_metros - sum(trechos)
    # Três trechos de ~1° cada, e a volta de ~3° da última parada para casa.
    assert abs(volta - 3 * trechos[0]) <= 3


def test_empate_de_distancia_desempata_pelo_menor_identificador():
    norte = (8, "Norte", Ponto(1.0, 0.0))
    sul = (4, "Sul", Ponto(-1.0, 0.0))
    rota = ordenar_pelo_mais_proximo(ORIGEM, [norte, sul])

    assert rota.paradas[0].mercado_id == 4
