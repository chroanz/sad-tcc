"""Testes do cálculo de distância em linha reta."""

import math

from app.otimizacao.logistica import Ponto, distancia_em_linha_reta_metros, metros_para_km

CENTRO_JUAZEIRO = Ponto(-7.2131, -39.3153)


def test_distancia_de_um_ponto_para_ele_mesmo_e_zero():
    assert distancia_em_linha_reta_metros(CENTRO_JUAZEIRO, CENTRO_JUAZEIRO) == 0


def test_um_grau_de_latitude_equivale_a_cerca_de_111_km():
    distancia = distancia_em_linha_reta_metros(Ponto(-7.0, -39.3153), Ponto(-8.0, -39.3153))
    assert abs(distancia - 111_195) < 5


def test_um_grau_de_longitude_encolhe_com_o_cosseno_da_latitude():
    """Perto do equador (-7,2°) um grau de longitude vale ~110,3 km."""
    distancia = distancia_em_linha_reta_metros(Ponto(-7.2131, -39.0), Ponto(-7.2131, -40.0))
    esperado = 111_195 * math.cos(math.radians(7.2131))
    assert abs(distancia - esperado) < 5


def test_diagonal_e_a_hipotenusa_dos_dois_catetos():
    destino = Ponto(-8.2131, -40.3153)
    cateto_norte_sul = distancia_em_linha_reta_metros(CENTRO_JUAZEIRO, Ponto(-8.2131, -39.3153))
    distancia = distancia_em_linha_reta_metros(CENTRO_JUAZEIRO, destino)
    assert distancia > cateto_norte_sul
    assert distancia < 2 * cateto_norte_sul


def test_distancia_e_simetrica():
    fortaleza = Ponto(-3.7319, -38.5267)
    ida = distancia_em_linha_reta_metros(CENTRO_JUAZEIRO, fortaleza)
    volta = distancia_em_linha_reta_metros(fortaleza, CENTRO_JUAZEIRO)
    assert ida == volta


def test_supermercados_do_catalogo_ficam_dentro_do_recorte_de_7_km():
    """Os supermercados fictícios foram espalhados num raio de 6 km do centro."""
    mercados = [
        Ponto(-7.213100, -39.308032),
        Ponto(-7.252914, -39.320500),
        Ponto(-7.163770, -39.336109),
    ]
    for mercado in mercados:
        assert distancia_em_linha_reta_metros(CENTRO_JUAZEIRO, mercado) < 7_000


def test_juazeiro_a_fortaleza_fica_perto_dos_400_km():
    """Ordem de grandeza conferida com a distância geodésica publicada (~395 km)."""
    distancia = distancia_em_linha_reta_metros(CENTRO_JUAZEIRO, Ponto(-3.7319, -38.5267))
    assert 390_000 < distancia < 405_000


def test_conversao_para_km_arredonda_para_tres_casas():
    assert metros_para_km(1234) == 1.234
    assert metros_para_km(0) == 0.0
