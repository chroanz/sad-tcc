"""Formulação e resolução do modelo de alocação de compras com OR-Tools CP-SAT.

Este módulo é o núcleo acadêmico do trabalho. Ele traduz a lista de compras e as ofertas
candidatas em um programa inteiro binário multiobjetivo, escalarizado por soma ponderada,
e o resolve com ``ortools.sat.python.cp_model``.

Notação (detalhada em ``docs/formulacao-matematica.md``):

* conjuntos: ``I`` itens da lista, ``J`` mercados, ``C ⊆ I × J`` pares candidatos;
* variáveis: ``comprar[i][j]``, ``visitar[j]`` e ``nao_atendido[i]``, todas binárias;
* objetivo: custo dos produtos mais o custo logístico ponderado, mais a penalidade dos
  itens não atendidos.

Toda a aritmética do solver é **inteira**. Dinheiro entra em centavos, distância entra em
metros e o peso de conveniência — único parâmetro em ponto flutuante — é escalado por
:data:`ESCALA_PESO`. O objetivo é montado na unidade de *centésimo de centavo*, o que
elimina qualquer divisão dentro do modelo e torna o valor ótimo exatamente reprodutível.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from ortools.sat.python import cp_model

from app.configuracao import CONFIGURACAO
from app.esquemas import (
    CandidatoEntrada,
    CompraPorMercado,
    Diagnostico,
    Economia,
    ItemComprado,
    ItemNaoAtendido,
    MotivoNaoAtendido,
    ParadaRota,
    RequisicaoOtimizacao,
    RespostaOtimizacao,
    StatusOtimizacao,
)
from app.otimizacao.economia import ItemParaEconomia, calcular_economia
from app.otimizacao.logistica import Ponto, distancia_ida_volta_metros, metros_para_km
from app.otimizacao.rota import MercadoParaRota, RotaCalculada, ordenar_rota

ESCALA_PESO = 100
"""Fator de escala do ``peso_conveniencia``: o objetivo é medido em centésimos de centavo."""

METROS_POR_KM = 1000


def arredondar_meio_para_cima(valor: float) -> int:
    """Arredonda para o inteiro mais próximo, com o meio sempre para cima.

    A função embutida ``round`` do Python usa arredondamento bancário (``round(0.5) == 0``),
    o que tornaria o custo de um item dependente da paridade do resultado. Aqui o critério
    é único e explícito, exigido pela reprodutibilidade da validação da Fase 4.

    Args:
        valor: número real a arredondar.

    Returns:
        O inteiro mais próximo; ``x.5`` sempre sobe.
    """
    return math.floor(valor + 0.5)


@dataclass(frozen=True)
class _ParCandidato:
    """Par (item, mercado) elegível: existe preço e o estoque cobre a quantidade pedida.

    Attributes:
        indice_item: posição do item na lista da requisição.
        mercado_id: mercado da oferta.
        custo_centavos: ``round(preco_unitario_centavos · quantidade)``.
        candidato: a oferta original, preservada para compor a resposta.
    """

    indice_item: int
    mercado_id: int
    custo_centavos: int
    candidato: CandidatoEntrada


@dataclass
class _Instancia:
    """Dados derivados da requisição, já em aritmética inteira.

    Attributes:
        requisicao: payload original.
        ordem_mercados: ``mercado_id`` na ordem de declaração, usada para indexar.
        metros_ida_volta: ``2 · d(origem, j)`` em metros inteiros, por mercado.
        custo_logistico_centavos: custo de visitar um mercado isoladamente (visita + km).
        pares: pares candidatos elegíveis.
        peso_escalado: ``round(peso_conveniencia · 100)``.
        penalidade_centavos: penalidade por item não atendido.
    """

    requisicao: RequisicaoOtimizacao
    ordem_mercados: List[int] = field(default_factory=list)
    metros_ida_volta: Dict[int, int] = field(default_factory=dict)
    custo_logistico_centavos: Dict[int, int] = field(default_factory=dict)
    pares: List[_ParCandidato] = field(default_factory=list)
    peso_escalado: int = 0
    penalidade_centavos: int = 1


@dataclass
class _ModeloConstruido:
    """Modelo CP-SAT montado, com as referências necessárias para ler a solução.

    Attributes:
        modelo: instância de ``cp_model.CpModel``.
        comprar: variável binária de cada par candidato, indexada por ``(item, mercado)``.
        visitar: variável binária de cada mercado.
        nao_atendido: variável binária de cada item.
        objetivo: variável inteira igual à função objetivo escalada.
        desempate: variável inteira da ordem lexicográfica usada na segunda fase.
    """

    modelo: cp_model.CpModel
    comprar: Dict[Tuple[int, int], cp_model.IntVar]
    visitar: Dict[int, cp_model.IntVar]
    nao_atendido: List[cp_model.IntVar]
    objetivo: cp_model.IntVar
    desempate: cp_model.IntVar


def _preparar_instancia(requisicao: RequisicaoOtimizacao) -> _Instancia:
    """Converte a requisição validada nos coeficientes inteiros do modelo.

    Filtra os candidatos pela restrição de estoque (``quantidade_disponivel >=
    quantidade``), calcula o custo de cada par, a distância linearizada de ida e volta de
    cada mercado e a penalidade de não atendimento.

    Args:
        requisicao: payload já validado pelo Pydantic.

    Returns:
        A instância derivada, pronta para a construção do modelo.
    """
    instancia = _Instancia(requisicao=requisicao)
    origem = Ponto(requisicao.origem.latitude, requisicao.origem.longitude)

    for mercado in requisicao.mercados:
        metros = distancia_ida_volta_metros(origem, Ponto(mercado.latitude, mercado.longitude))
        instancia.ordem_mercados.append(mercado.mercado_id)
        instancia.metros_ida_volta[mercado.mercado_id] = metros
        instancia.custo_logistico_centavos[mercado.mercado_id] = (
            requisicao.custo_por_visita_centavos
            + arredondar_meio_para_cima(requisicao.custo_por_km_centavos * metros / METROS_POR_KM)
        )

    for indice_item, item in enumerate(requisicao.itens):
        for candidato in item.candidatos:
            if candidato.quantidade_disponivel < item.quantidade:
                continue
            instancia.pares.append(
                _ParCandidato(
                    indice_item=indice_item,
                    mercado_id=candidato.mercado_id,
                    custo_centavos=arredondar_meio_para_cima(
                        candidato.preco_unitario_centavos * item.quantidade
                    ),
                    candidato=candidato,
                )
            )

    instancia.peso_escalado = arredondar_meio_para_cima(requisicao.peso_conveniencia * ESCALA_PESO)
    instancia.penalidade_centavos = _calcular_penalidade(instancia)
    return instancia


def _calcular_penalidade(instancia: _Instancia) -> int:
    """Calcula a penalidade de não atendimento de um item.

    O valor não é um "número grande mágico": ele é a **maior economia concebível** obtida
    ao abandonar um item, mais um centavo. Deixar um item fora da solução pode, no melhor
    dos casos, poupar o custo de todos os pares candidatos da instância somado a toda a
    parcela logística ponderada possível. Somando 1 a esse teto, qualquer solução que
    deixe de atender um item atendível fica estritamente pior que a alternativa que o
    atende — a penalidade nunca distorce a comparação entre soluções viáveis.

    Args:
        instancia: instância já com pares e custos logísticos calculados.

    Returns:
        A penalidade, em centavos.
    """
    teto_itens = sum(par.custo_centavos for par in instancia.pares)
    teto_logistico_escalado = instancia.peso_escalado * sum(
        instancia.custo_logistico_centavos.values()
    )
    teto_logistico = -(-teto_logistico_escalado // ESCALA_PESO)
    return teto_itens + teto_logistico + 1


def _construir_modelo(instancia: _Instancia) -> _ModeloConstruido:
    """Monta as variáveis, as restrições e as duas expressões objetivo do modelo.

    Variáveis:

    * ``comprar[i][j] ∈ {0,1}`` — criada **apenas** para pares candidatos, isto é, quando
      existe preço cadastrado e o estoque cobre a quantidade pedida;
    * ``visitar[j] ∈ {0,1}`` — o mercado ``j`` entra no roteiro;
    * ``nao_atendido[i] ∈ {0,1}`` — o item ``i`` fica sem alocação.

    Restrições:

    * atribuição exata: ``Σ_j comprar[i][j] + nao_atendido[i] = 1`` para todo item, o que
      proíbe dividir a quantidade de um item entre mercados (RN01) e dá a todo item um
      destino explícito;
    * acoplamento: ``comprar[i][j] ≤ visitar[j]``, só se compra onde se visita (RN02).

    Args:
        instancia: dados derivados da requisição.

    Returns:
        O modelo construído com as referências para leitura da solução.
    """
    modelo = cp_model.CpModel()

    visitar = {
        mercado_id: modelo.NewBoolVar(f"visitar_{mercado_id}")
        for mercado_id in instancia.ordem_mercados
    }
    nao_atendido = [
        modelo.NewBoolVar(f"nao_atendido_{item.item_id}") for item in instancia.requisicao.itens
    ]
    comprar: Dict[Tuple[int, int], cp_model.IntVar] = {}
    alternativas_por_item: Dict[int, List[cp_model.IntVar]] = {}
    for par in instancia.pares:
        chave = (par.indice_item, par.mercado_id)
        variavel = modelo.NewBoolVar(f"comprar_{chave[0]}_{chave[1]}")
        comprar[chave] = variavel
        alternativas_por_item.setdefault(par.indice_item, []).append(variavel)

    for indice_item in range(len(instancia.requisicao.itens)):
        alternativas = alternativas_por_item.get(indice_item, [])
        modelo.Add(sum(alternativas) + nao_atendido[indice_item] == 1)

    for (_, mercado_id), variavel in comprar.items():
        modelo.Add(variavel <= visitar[mercado_id])

    termo_itens = sum(
        par.custo_centavos * comprar[(par.indice_item, par.mercado_id)] for par in instancia.pares
    )
    termo_logistico = sum(
        instancia.custo_logistico_centavos[mercado_id] * variavel
        for mercado_id, variavel in visitar.items()
    )
    termo_penalidade = sum(nao_atendido)

    teto_objetivo = (
        ESCALA_PESO * sum(par.custo_centavos for par in instancia.pares)
        + instancia.peso_escalado * sum(instancia.custo_logistico_centavos.values())
        + ESCALA_PESO * instancia.penalidade_centavos * len(nao_atendido)
        + 1
    )
    objetivo = modelo.NewIntVar(0, teto_objetivo, "objetivo_escalado")
    modelo.Add(
        objetivo
        == ESCALA_PESO * termo_itens
        + instancia.peso_escalado * termo_logistico
        + ESCALA_PESO * instancia.penalidade_centavos * termo_penalidade
    )

    metros_totais = sum(instancia.metros_ida_volta.values())
    fator_lexicografico = metros_totais + 1
    teto_desempate = fator_lexicografico * len(visitar) + metros_totais + 1
    desempate = modelo.NewIntVar(0, teto_desempate, "desempate_lexicografico")
    modelo.Add(
        desempate
        == fator_lexicografico * sum(visitar.values())
        + sum(
            instancia.metros_ida_volta[mercado_id] * variavel
            for mercado_id, variavel in visitar.items()
        )
    )

    return _ModeloConstruido(
        modelo=modelo,
        comprar=comprar,
        visitar=visitar,
        nao_atendido=nao_atendido,
        objetivo=objetivo,
        desempate=desempate,
    )


def _criar_solver(limite_tempo_segundos: float) -> cp_model.CpSolver:
    """Instancia o solver CP-SAT com os parâmetros de reprodutibilidade da Fase 4.

    A busca roda com uma única thread e semente fixa: o CP-SAT paralelo é não
    determinístico por construção (a ordem de chegada das subsoluções varia), e o
    experimento de acurácia exige que a mesma entrada produza sempre a mesma saída.

    Args:
        limite_tempo_segundos: teto de tempo aplicado a esta fase do solve.

    Returns:
        O solver configurado.
    """
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = limite_tempo_segundos
    solver.parameters.random_seed = CONFIGURACAO.semente_solver
    solver.parameters.num_search_workers = 1
    return solver


def _traduzir_status(status: int) -> StatusOtimizacao:
    """Traduz o status do CP-SAT para o enum do contrato.

    Args:
        status: código devolvido por ``CpSolver.Solve``.

    Returns:
        ``OTIMO`` para ``OPTIMAL``, ``VIAVEL`` para ``FEASIBLE`` e ``INVIAVEL`` no resto.
    """
    if status == cp_model.OPTIMAL:
        return StatusOtimizacao.OTIMO
    if status == cp_model.FEASIBLE:
        return StatusOtimizacao.VIAVEL
    return StatusOtimizacao.INVIAVEL


def _ler_solucao(
    solver: cp_model.CpSolver, construido: _ModeloConstruido, instancia: _Instancia
) -> Tuple[Dict[int, _ParCandidato], List[int]]:
    """Extrai a alocação e o conjunto de mercados visitados de uma solução.

    Args:
        solver: solver com uma solução carregada.
        construido: modelo correspondente àquele solver.
        instancia: instância que originou o modelo.

    Returns:
        Um par ``(alocacao, visitados)``, onde ``alocacao`` mapeia o índice do item ao par
        candidato escolhido e ``visitados`` lista os ``mercado_id`` com ``visitar[j] = 1``,
        na ordem de declaração da requisição.
    """
    alocacao: Dict[int, _ParCandidato] = {}
    for par in instancia.pares:
        if solver.Value(construido.comprar[(par.indice_item, par.mercado_id)]) == 1:
            alocacao[par.indice_item] = par

    visitados = [
        mercado_id
        for mercado_id in instancia.ordem_mercados
        if solver.Value(construido.visitar[mercado_id]) == 1
    ]
    return alocacao, visitados


def _motivo_do_item(item_index: int, instancia: _Instancia) -> MotivoNaoAtendido:
    """Classifica por que um item ficou sem alocação.

    Args:
        item_index: posição do item na requisição.
        instancia: instância em resolução.

    Returns:
        ``SEM_CANDIDATO`` quando não há preço cadastrado em mercado nenhum e
        ``SEM_CANDIDATO_COM_ESTOQUE`` quando há preço mas nenhum estoque suficiente.
    """
    if not instancia.requisicao.itens[item_index].candidatos:
        return MotivoNaoAtendido.SEM_CANDIDATO
    return MotivoNaoAtendido.SEM_CANDIDATO_COM_ESTOQUE


def _montar_compras(
    alocacao: Dict[int, _ParCandidato],
    instancia: _Instancia,
    ordem_de_visita: Sequence[int],
) -> List[CompraPorMercado]:
    """Agrupa os itens alocados por mercado, na ordem da rota sugerida.

    Args:
        alocacao: item → par candidato escolhido.
        instancia: instância em resolução.
        ordem_de_visita: ``mercado_id`` na ordem em que a rota os visita.

    Returns:
        A lista ``compras_por_mercado`` do contrato.
    """
    nomes = {mercado.mercado_id: mercado.nome for mercado in instancia.requisicao.mercados}
    agrupado: Dict[int, List[ItemComprado]] = {}
    for indice_item, par in sorted(alocacao.items()):
        item = instancia.requisicao.itens[indice_item]
        agrupado.setdefault(par.mercado_id, []).append(
            ItemComprado(
                item_id=item.item_id,
                descricao=item.descricao,
                marca_id=par.candidato.marca_id,
                marca_nome=par.candidato.marca_nome,
                quantidade=item.quantidade,
                unidade=item.unidade,
                preco_unitario_centavos=par.candidato.preco_unitario_centavos,
                custo_centavos=par.custo_centavos,
            )
        )

    restantes = [mercado_id for mercado_id in agrupado if mercado_id not in ordem_de_visita]
    sequencia = list(ordem_de_visita) + sorted(restantes)

    compras: List[CompraPorMercado] = []
    for mercado_id in sequencia:
        itens = agrupado.get(mercado_id)
        if not itens:
            continue
        compras.append(
            CompraPorMercado(
                mercado_id=mercado_id,
                nome=nomes.get(mercado_id, ""),
                subtotal_centavos=sum(comprado.custo_centavos for comprado in itens),
                itens=itens,
            )
        )
    return compras


def _montar_economia(alocacao: Dict[int, _ParCandidato], instancia: _Instancia) -> Economia:
    """Prepara os dados do baseline de mercado único e delega o cálculo.

    Args:
        alocacao: item → par candidato escolhido.
        instancia: instância em resolução.

    Returns:
        O bloco ``economia`` do contrato.
    """
    custos_por_item: Dict[int, Dict[int, int]] = {}
    for par in instancia.pares:
        custos_por_item.setdefault(par.indice_item, {})[par.mercado_id] = par.custo_centavos

    itens_para_economia = [
        ItemParaEconomia(
            item_id=instancia.requisicao.itens[indice_item].item_id,
            mercado_escolhido=par.mercado_id,
            custo_escolhido_centavos=par.custo_centavos,
            custo_por_mercado_centavos=custos_por_item.get(indice_item, {}),
        )
        for indice_item, par in sorted(alocacao.items())
    ]
    nomes = {mercado.mercado_id: mercado.nome for mercado in instancia.requisicao.mercados}
    return calcular_economia(itens_para_economia, instancia.custo_logistico_centavos, nomes)


def _montar_rota(visitados: Sequence[int], instancia: _Instancia) -> RotaCalculada:
    """Ordena os mercados visitados a partir da origem do usuário.

    Args:
        visitados: ``mercado_id`` selecionados pelo modelo.
        instancia: instância em resolução.

    Returns:
        A rota calculada, com paradas e distância total real.
    """
    por_id = {mercado.mercado_id: mercado for mercado in instancia.requisicao.mercados}
    mercados = [
        MercadoParaRota(
            mercado_id=mercado_id,
            nome=por_id[mercado_id].nome,
            ponto=Ponto(por_id[mercado_id].latitude, por_id[mercado_id].longitude),
        )
        for mercado_id in visitados
    ]
    origem = Ponto(instancia.requisicao.origem.latitude, instancia.requisicao.origem.longitude)
    return ordenar_rota(origem, mercados)


def resolver_alocacao_de_compras(requisicao: RequisicaoOtimizacao) -> RespostaOtimizacao:
    """Resolve o modelo de alocação de compras e devolve a recomendação completa.

    O solve tem **duas fases**, exigidas pelo desempate determinístico do contrato:

    1. minimiza a função objetivo escalarizada e guarda o valor ótimo ``Z*``;
    2. fixa ``objetivo == Z*`` e minimiza, em ordem lexicográfica, o número de mercados
       visitados e depois a distância linearizada total. A ordem lexicográfica é obtida
       por um único escalar ``(Σ_j metros_j + 1) · Σ_j visitar[j] + Σ_j metros_j ·
       visitar[j]``: como a segunda parcela é sempre menor que o fator multiplicativo, o
       primeiro critério domina o segundo sem ambiguidade.

    ``valor_objetivo_centavos`` reporta sempre o ``Z*`` da primeira fase, descontadas as
    penalidades de não atendimento — que são artefato de modelagem, não gasto do usuário.

    Nenhum cenário de borda levanta exceção: lista vazia, item sem candidato, mercado único
    e instância totalmente inatendível devolvem ``200`` com os campos zerados ou nulos.

    Args:
        requisicao: payload validado de ``POST /otimizar``.

    Returns:
        A resposta completa do contrato: status, decomposição de custos, rota, compras por
        mercado, itens não atendidos, economia e diagnóstico do solver.
    """
    instancia = _preparar_instancia(requisicao)

    primeira_fase = _construir_modelo(instancia)
    solver_fase_um = _criar_solver(requisicao.limite_tempo_segundos)
    primeira_fase.modelo.Minimize(primeira_fase.objetivo)
    status_fase_um = solver_fase_um.Solve(primeira_fase.modelo)

    tempo_total = solver_fase_um.WallTime()
    quantidade_variaveis = len(primeira_fase.modelo.Proto().variables)
    quantidade_restricoes = len(primeira_fase.modelo.Proto().constraints)
    status = _traduzir_status(status_fase_um)

    if status is StatusOtimizacao.INVIAVEL:
        return _resposta_sem_solucao(
            instancia,
            status,
            solver_fase_um.StatusName(status_fase_um),
            tempo_total,
            quantidade_variaveis,
            quantidade_restricoes,
        )

    valor_otimo_escalado = solver_fase_um.Value(primeira_fase.objetivo)
    alocacao, visitados = _ler_solucao(solver_fase_um, primeira_fase, instancia)

    segunda_fase = _construir_modelo(instancia)
    segunda_fase.modelo.Add(segunda_fase.objetivo == valor_otimo_escalado)
    segunda_fase.modelo.Minimize(segunda_fase.desempate)
    solver_fase_dois = _criar_solver(requisicao.limite_tempo_segundos)
    status_fase_dois = solver_fase_dois.Solve(segunda_fase.modelo)
    tempo_total += solver_fase_dois.WallTime()

    if status_fase_dois in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        alocacao, visitados = _ler_solucao(solver_fase_dois, segunda_fase, instancia)

    return _montar_resposta(
        instancia=instancia,
        status=status,
        status_solver=solver_fase_um.StatusName(status_fase_um),
        valor_otimo_escalado=valor_otimo_escalado,
        alocacao=alocacao,
        visitados=visitados,
        tempo_total=tempo_total,
        quantidade_variaveis=quantidade_variaveis,
        quantidade_restricoes=quantidade_restricoes,
    )


def _resposta_sem_solucao(
    instancia: _Instancia,
    status: StatusOtimizacao,
    status_solver: str,
    tempo_total: float,
    quantidade_variaveis: int,
    quantidade_restricoes: int,
) -> RespostaOtimizacao:
    """Monta a resposta quando o solver não encontra nenhuma solução.

    Args:
        instancia: instância em resolução.
        status: status agregado (``INVIAVEL``).
        status_solver: nome do status devolvido pelo CP-SAT.
        tempo_total: tempo acumulado de solve.
        quantidade_variaveis: variáveis do modelo da primeira fase.
        quantidade_restricoes: restrições do modelo da primeira fase.

    Returns:
        Uma resposta ``200`` com custos zerados e todos os itens não atendidos.
    """
    nao_atendidos = [
        ItemNaoAtendido(
            item_id=item.item_id,
            descricao=item.descricao,
            motivo=_motivo_do_item(indice, instancia),
        )
        for indice, item in enumerate(instancia.requisicao.itens)
    ]
    return RespostaOtimizacao(
        status=status,
        custo_itens_centavos=0,
        custo_logistico_centavos=0,
        custo_total_centavos=0,
        valor_objetivo_centavos=0,
        peso_conveniencia=instancia.requisicao.peso_conveniencia,
        quantidade_mercados_visitados=0,
        distancia_total_km=0.0,
        rota=[],
        compras_por_mercado=[],
        itens_nao_atendidos=nao_atendidos,
        economia=calcular_economia([], instancia.custo_logistico_centavos, {}),
        diagnostico=Diagnostico(
            status_solver=status_solver,
            tempo_solver_segundos=round(tempo_total, 6),
            quantidade_variaveis=quantidade_variaveis,
            quantidade_restricoes=quantidade_restricoes,
        ),
    )


def _montar_resposta(
    instancia: _Instancia,
    status: StatusOtimizacao,
    status_solver: str,
    valor_otimo_escalado: int,
    alocacao: Dict[int, _ParCandidato],
    visitados: List[int],
    tempo_total: float,
    quantidade_variaveis: int,
    quantidade_restricoes: int,
) -> RespostaOtimizacao:
    """Traduz a solução do solver na resposta do contrato.

    ``custo_logistico_centavos`` é reportado **sem** o peso, como manda o contrato: ele é o
    que o usuário de fato despende com deslocamento. O peso aparece apenas em
    ``valor_objetivo_centavos``.

    Args:
        instancia: instância em resolução.
        status: status agregado da primeira fase.
        status_solver: nome do status do CP-SAT.
        valor_otimo_escalado: ``Z*`` na unidade escalada (centésimo de centavo).
        alocacao: item → par candidato escolhido.
        visitados: mercados com ``visitar[j] = 1``.
        tempo_total: tempo acumulado das duas fases.
        quantidade_variaveis: variáveis do modelo da primeira fase.
        quantidade_restricoes: restrições do modelo da primeira fase.

    Returns:
        A resposta completa de ``POST /otimizar``.
    """
    custo_itens = sum(par.custo_centavos for par in alocacao.values())
    custo_logistico = sum(
        instancia.custo_logistico_centavos[mercado_id] for mercado_id in visitados
    )
    quantidade_nao_atendidos = len(instancia.requisicao.itens) - len(alocacao)
    objetivo_sem_penalidade = valor_otimo_escalado - (
        ESCALA_PESO * instancia.penalidade_centavos * quantidade_nao_atendidos
    )
    valor_objetivo = arredondar_meio_para_cima(objetivo_sem_penalidade / ESCALA_PESO)

    rota_calculada = _montar_rota(visitados, instancia)
    paradas = [
        ParadaRota(
            ordem=posicao,
            mercado_id=parada.mercado_id,
            nome=parada.nome,
            distancia_do_anterior_km=metros_para_km(parada.distancia_do_anterior_metros),
        )
        for posicao, parada in enumerate(rota_calculada.paradas, start=1)
    ]
    ordem_de_visita = [parada.mercado_id for parada in rota_calculada.paradas]

    nao_atendidos = [
        ItemNaoAtendido(
            item_id=item.item_id,
            descricao=item.descricao,
            motivo=_motivo_do_item(indice, instancia),
        )
        for indice, item in enumerate(instancia.requisicao.itens)
        if indice not in alocacao
    ]

    return RespostaOtimizacao(
        status=status,
        custo_itens_centavos=custo_itens,
        custo_logistico_centavos=custo_logistico,
        custo_total_centavos=custo_itens + custo_logistico,
        valor_objetivo_centavos=valor_objetivo,
        peso_conveniencia=instancia.requisicao.peso_conveniencia,
        quantidade_mercados_visitados=len(visitados),
        distancia_total_km=metros_para_km(rota_calculada.distancia_total_metros),
        rota=paradas,
        compras_por_mercado=_montar_compras(alocacao, instancia, ordem_de_visita),
        itens_nao_atendidos=nao_atendidos,
        economia=_montar_economia(alocacao, instancia),
        diagnostico=Diagnostico(
            status_solver=status_solver,
            tempo_solver_segundos=round(tempo_total, 6),
            quantidade_variaveis=quantidade_variaveis,
            quantidade_restricoes=quantidade_restricoes,
        ),
    )


def calcular_custo_de_uma_alocacao(
    requisicao: RequisicaoOtimizacao, alocacao: Dict[int, Optional[int]]
) -> int:
    """Avalia a função objetivo escalada para uma alocação arbitrária.

    Existe para os testes e para a inspeção manual do modelo: dada uma atribuição
    item → mercado (ou ``None`` para item não atendido), devolve o valor exato do objetivo
    na mesma unidade usada pelo solver.

    Args:
        requisicao: payload da instância.
        alocacao: índice do item → ``mercado_id`` escolhido, ou ``None``.

    Returns:
        O valor do objetivo escalado (centésimo de centavo).

    Raises:
        ValueError: se a alocação usar um par que não é candidato elegível.
    """
    instancia = _preparar_instancia(requisicao)
    custos = {(par.indice_item, par.mercado_id): par.custo_centavos for par in instancia.pares}

    total_itens = 0
    visitados = set()
    nao_atendidos = 0
    for indice_item in range(len(requisicao.itens)):
        mercado_id = alocacao.get(indice_item)
        if mercado_id is None:
            nao_atendidos += 1
            continue
        chave = (indice_item, mercado_id)
        if chave not in custos:
            raise ValueError(f"par {chave} nao e um candidato elegivel")
        total_itens += custos[chave]
        visitados.add(mercado_id)

    total_logistico = sum(instancia.custo_logistico_centavos[j] for j in visitados)
    return (
        ESCALA_PESO * total_itens
        + instancia.peso_escalado * total_logistico
        + ESCALA_PESO * instancia.penalidade_centavos * nao_atendidos
    )
