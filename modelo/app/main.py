"""Aplicação FastAPI do serviço de otimização.

Expõe apenas dois endpoints, conforme ``docs/contrato-otimizacao.md``:

* ``GET /saude`` — usado pelo healthcheck do Docker Compose e pela verificação de
  disponibilidade que a API Go faz antes de aceitar pedidos de recomendação;
* ``POST /otimizar`` — resolve o modelo CP-SAT e devolve a recomendação.

O serviço é stateless: não abre conexão com banco, não guarda sessão e não conhece o
usuário. Toda a entrada chega no corpo da requisição.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.configuracao import CONFIGURACAO
from app.esquemas import RequisicaoOtimizacao, RespostaOtimizacao, RespostaSaude
from app.otimizacao.modelo_cpsat import resolver_alocacao_de_compras

NOME_DO_SERVICO = "modelo-otimizacao"

app = FastAPI(
    title="Serviço de otimização de compras",
    description=(
        "Núcleo de decisão do SAD de compras de supermercado: recebe a lista de compras "
        "com os candidatos de preço e disponibilidade por mercado e devolve a alocação ótima."
    ),
    version=CONFIGURACAO.versao,
)


@app.get("/saude", response_model=RespostaSaude, summary="Verificação de disponibilidade")
def verificar_saude() -> RespostaSaude:
    """Informa que o serviço está no ar.

    Returns:
        O identificador do serviço e a versão em execução.
    """
    return RespostaSaude(status="ok", servico=NOME_DO_SERVICO, versao=CONFIGURACAO.versao)


def _validar_teto_da_poc(requisicao: RequisicaoOtimizacao) -> None:
    """Rejeita instâncias acima do teto declarado da PoC (RNF03 / CB10).

    O teto de mercados cobre o catálogo inteiro da PoC (as cidades da base do DIEESE); ele
    existe para que uma instância fora do escopo seja recusada, e não resolvida em silêncio.

    Args:
        requisicao: payload já validado pelo Pydantic.

    Raises:
        HTTPException: ``422`` com mensagem descritiva quando o teto é ultrapassado.
    """
    if len(requisicao.itens) > CONFIGURACAO.maximo_itens:
        raise HTTPException(
            status_code=422,
            detail=(
                f"instancia acima do teto da PoC: {len(requisicao.itens)} itens, "
                f"maximo {CONFIGURACAO.maximo_itens}"
            ),
        )
    if len(requisicao.mercados) > CONFIGURACAO.maximo_mercados:
        raise HTTPException(
            status_code=422,
            detail=(
                f"instancia acima do teto da PoC: {len(requisicao.mercados)} mercados, "
                f"maximo {CONFIGURACAO.maximo_mercados}"
            ),
        )


@app.post("/otimizar", response_model=RespostaOtimizacao, summary="Resolver a alocação")
def otimizar(requisicao: RequisicaoOtimizacao) -> RespostaOtimizacao:
    """Resolve o modelo de alocação de compras para a lista recebida.

    Casos de borda — lista vazia, item sem candidato, estoque insuficiente, mercado único e
    instância totalmente inatendível — devolvem ``200`` com os campos apropriados, nunca
    erro. Só há ``422`` para payload inválido e ``500`` para falha inesperada do solver.

    Args:
        requisicao: payload de ``POST /otimizar``.

    Returns:
        A recomendação completa: alocação, ordem de visita, decomposição de custos e economia.

    Raises:
        HTTPException: ``422`` para instância acima do teto da PoC; ``500`` se o solver
            falhar de forma inesperada.
    """
    _validar_teto_da_poc(requisicao)
    try:
        return resolver_alocacao_de_compras(requisicao)
    except Exception as erro:  # noqa: BLE001 - a borda HTTP traduz qualquer falha em 500
        raise HTTPException(
            status_code=500, detail=f"falha ao resolver o modelo de otimizacao: {erro}"
        ) from erro
