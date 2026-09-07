"""Testes dos endpoints HTTP do serviço de otimização.

Verificam o contrato na fronteira: forma da resposta, validações que devem devolver 422 e
os casos de borda que precisam responder 200 em vez de erro.
"""

from typing import Any, Dict

from fastapi.testclient import TestClient

from app.main import app
from testes.apoio import CENTRO_JUAZEIRO, montar_item, montar_mercado

cliente = TestClient(app)


def montar_corpo(**substituicoes: Any) -> Dict[str, Any]:
    """Monta um corpo válido de ``POST /otimizar``, com substituições pontuais.

    Args:
        **substituicoes: campos a sobrescrever no corpo padrão.

    Returns:
        O dicionário pronto para ser enviado como JSON.
    """
    corpo: Dict[str, Any] = {
        "origem": CENTRO_JUAZEIRO,
        "peso_conveniencia": 1.0,
        "mercados": [montar_mercado(1), montar_mercado(5)],
        "itens": [montar_item(1, [(1, 2599), (5, 2399)])],
    }
    corpo.update(substituicoes)
    return corpo


def test_saude_responde_ok():
    resposta = cliente.get("/saude")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "ok"
    assert corpo["servico"] == "modelo-otimizacao"


def test_otimizar_devolve_a_estrutura_completa_do_contrato():
    resposta = cliente.post("/otimizar", json=montar_corpo())

    assert resposta.status_code == 200
    corpo = resposta.json()
    campos_esperados = {
        "status",
        "custo_itens_centavos",
        "custo_logistico_centavos",
        "custo_total_centavos",
        "valor_objetivo_centavos",
        "peso_conveniencia",
        "quantidade_mercados_visitados",
        "distancia_total_km",
        "rota",
        "compras_por_mercado",
        "itens_nao_atendidos",
        "economia",
        "diagnostico",
    }
    assert campos_esperados.issubset(corpo.keys())
    assert corpo["status"] in {"OTIMO", "VIAVEL", "INVIAVEL"}


def test_lista_vazia_responde_200_e_nao_erro():
    resposta = cliente.post("/otimizar", json=montar_corpo(itens=[]))

    assert resposta.status_code == 200
    assert resposta.json()["custo_total_centavos"] == 0


def test_item_sem_oferta_responde_200_com_nao_atendido():
    corpo = montar_corpo(itens=[montar_item(1, [])])
    resposta = cliente.post("/otimizar", json=corpo)

    assert resposta.status_code == 200
    assert resposta.json()["itens_nao_atendidos"][0]["motivo"] == "SEM_CANDIDATO"


def test_candidato_em_mercado_desconhecido_e_rejeitado():
    """Regra 1 do contrato."""
    corpo = montar_corpo(
        mercados=[montar_mercado(1)],
        itens=[montar_item(1, [(1, 2599), (5, 2399)])],
    )
    assert cliente.post("/otimizar", json=corpo).status_code == 422


def test_mercado_repetido_e_rejeitado():
    """Regra 2 do contrato."""
    corpo = montar_corpo(mercados=[montar_mercado(1), montar_mercado(1)])
    assert cliente.post("/otimizar", json=corpo).status_code == 422


def test_item_repetido_e_rejeitado():
    """Regra 2 do contrato."""
    corpo = montar_corpo(itens=[montar_item(1, [(1, 100)]), montar_item(1, [(5, 100)])])
    assert cliente.post("/otimizar", json=corpo).status_code == 422


def test_par_item_mercado_duplicado_e_rejeitado():
    """Regra 3 do contrato."""
    corpo = montar_corpo(itens=[montar_item(1, [(1, 100), (1, 200)])])
    assert cliente.post("/otimizar", json=corpo).status_code == 422


def test_preco_nao_positivo_e_rejeitado():
    """Regra 4 do contrato."""
    corpo = montar_corpo(itens=[montar_item(1, [(1, 0)])])
    assert cliente.post("/otimizar", json=corpo).status_code == 422


def test_coordenada_fora_de_faixa_e_rejeitada():
    """Regra 5 do contrato."""
    corpo = montar_corpo(origem={"latitude": -100.0, "longitude": -39.3153})
    assert cliente.post("/otimizar", json=corpo).status_code == 422


def test_peso_negativo_e_rejeitado():
    assert cliente.post("/otimizar", json=montar_corpo(peso_conveniencia=-1.0)).status_code == 422


def test_quantidade_nao_positiva_e_rejeitada():
    corpo = montar_corpo(itens=[montar_item(1, [(1, 100)], quantidade=0.0)])
    assert cliente.post("/otimizar", json=corpo).status_code == 422


def test_instancia_acima_do_teto_de_itens_e_rejeitada():
    """Teto da PoC: 20 itens."""
    itens = [montar_item(identificador, [(1, 1000)]) for identificador in range(1, 22)]
    resposta = cliente.post("/otimizar", json=montar_corpo(itens=itens))

    assert resposta.status_code == 422
    assert "teto" in resposta.json()["detail"].lower()


def test_instancia_dentro_do_teto_de_itens_e_aceita():
    itens = [montar_item(identificador, [(1, 1000)]) for identificador in range(1, 21)]
    assert cliente.post("/otimizar", json=montar_corpo(itens=itens)).status_code == 200
