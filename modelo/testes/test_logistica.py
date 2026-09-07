"""Testes do cálculo de distância."""

import math

from app.otimizacao.logistica import (
    Ponto,
    distancia_haversine_metros,
    distancia_ida_volta_metros,
    matriz_de_distancias_metros,
    metros_para_km,
)

CENTRO_JUAZEIRO = Ponto(-7.2131, -39.3153)


def test_distancia_de_um_ponto_para_ele_mesmo_e_zero():
    assert distancia_haversine_metros(CENTRO_JUAZEIRO, CENTRO_JUAZEIRO) == 0


def test_um_grau_de_latitude_equivale_a_cerca_de_111_km():
    """Um grau de latitude vale ~111,19 km em qualquer longitude."""
    distancia = distancia_haversine_metros(Ponto(-7.0, -39.3153), Ponto(-8.0, -39.3153))
    assert abs(distancia - 111_195) < 500


def test_um_grau_de_longitude_encolhe_com_o_cosseno_da_latitude():
    """Perto do equador (-7,2°) um grau de longitude vale ~110,4 km."""
    distancia = distancia_haversine_metros(Ponto(-7.2131, -39.0), Ponto(-7.2131, -40.0))
    esperado = 111_320 * math.cos(math.radians(7.2131))
    assert abs(distancia - esperado) < 500


def test_distancia_e_simetrica():
    ida = distancia_haversine_metros(CENTRO_JUAZEIRO, Ponto(-7.2470, -39.3460))
    volta = distancia_haversine_metros(Ponto(-7.2470, -39.3460), CENTRO_JUAZEIRO)
    assert ida == volta


def test_ida_e_volta_e_o_dobro_da_distancia_simples():
    destino = Ponto(-7.2470, -39.3460)
    assert distancia_ida_volta_metros(CENTRO_JUAZEIRO, destino) == 2 * distancia_haversine_metros(
        CENTRO_JUAZEIRO, destino
    )


def test_mercados_do_recorte_estao_dentro_do_raio_declarado():
    """Os seis mercados do escopo ficam a menos de 7 km do centro de Juazeiro do Norte."""
    mercados = [
        Ponto(-7.214500, -39.316800),
        Ponto(-7.204200, -39.320500),
        Ponto(-7.220800, -39.304200),
        Ponto(-7.235000, -39.330000),
        Ponto(-7.247000, -39.346000),
        Ponto(-7.264000, -39.279000),
    ]
    for mercado in mercados:
        assert distancia_haversine_metros(CENTRO_JUAZEIRO, mercado) < 7_000


def test_matriz_de_distancias_e_simetrica_com_diagonal_nula():
    pontos = [CENTRO_JUAZEIRO, Ponto(-7.2042, -39.3205), Ponto(-7.2470, -39.3460)]
    matriz = matriz_de_distancias_metros(pontos)

    assert len(matriz) == 3
    for indice in range(3):
        assert matriz[indice][indice] == 0
        for outro in range(3):
            assert matriz[indice][outro] == matriz[outro][indice]


def test_conversao_para_km_arredonda_para_tres_casas():
    assert metros_para_km(1234) == 1.234
    assert metros_para_km(0) == 0.0
