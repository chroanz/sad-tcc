"""Validação do CP-SAT por enumeração exaustiva (Fase 4 do TCC).

Exigido pela seção 5 do ``CLAUDE.md``. Gera instâncias pequenas com semente fixa, resolve
cada uma por **enumeração exaustiva de todas as atribuições possíveis** e compara o ótimo
encontrado com o que o CP-SAT devolve.

A enumeração aqui é uma **implementação independente**: ela não importa nada de
``app.otimizacao.modelo_cpsat`` além da função que está sob teste. O custo por par
item-mercado, o custo de conveniência e a função objetivo são reescritos do zero neste
arquivo. Se os dois lados compartilhassem a aritmética, a comparação não provaria nada.

O custo de conveniência de um conjunto de mercados visitados é apenas o custo fixo de cada
visita: a distância percorrida não é precificada, então não entra no objetivo e não
precisa ser enumerada aqui.

Método de comparação, em três passos por instância:

1. a enumeração percorre todas as atribuições viáveis e guarda o **menor** objetivo;
2. a alocação que o CP-SAT devolveu é reavaliada **pela aritmética da enumeração**;
3. os dois valores têm de ser idênticos. Além disso, nenhum item com candidato elegível
   pode ter ficado sem atendimento — é assim que se verifica que a penalidade de não
   atendimento é grande o bastante para nunca distorcer a solução.

Uso:
    python scripts/validacao_exaustiva.py --repeticoes 30
    python scripts/validacao_exaustiva.py --repeticoes 50 --semente 7 --saida relatorio.md
"""

import argparse
import itertools
import math
import os
import random
import sys
import time
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.esquemas import RequisicaoOtimizacao  # noqa: E402
from app.otimizacao.modelo_cpsat import resolver_alocacao_de_compras  # noqa: E402

# Reimplementação independente das constantes do contrato.
ESCALA_DO_PESO = 100

MENSAGEM_CONVERGENCIA_TOTAL = (
    "Convergência total: o CP-SAT encontrou o ótimo global em todas as instâncias."
)
MENSAGEM_DIVERGENCIA = (
    "**Divergência detectada.** Ver a coluna Observação nas linhas marcadas com NAO."
)

# Origem no centro de Juazeiro do Norte/CE; supermercados do catálogo, dentro da cidade.
CENTRO_DE_JUAZEIRO = (-7.2131, -39.3153)
MERCADOS_DO_RECORTE: List[Tuple[int, str, float, float]] = [
    (1, "Supermercado Brasília", -7.213100, -39.308032),
    (2, "Supermercado Cuiabá", -7.229162, -39.313879),
    (3, "Supermercado Rio de Janeiro", -7.225936, -39.294961),
    (4, "Supermercado Vitória", -7.237883, -39.328274),
    (5, "Supermercado Palmas", -7.252914, -39.320500),
    (6, "Supermercado Macaé", -7.163770, -39.336109),
]


class ResultadoDaInstancia(NamedTuple):
    """Linha da tabela de convergência.

    Attributes:
        indice: número sequencial da instância.
        quantidade_itens: itens da lista gerada.
        quantidade_mercados: mercados considerados.
        peso_conveniencia: peso usado na escalarização.
        objetivo_enumeracao: menor objetivo encontrado pela enumeração.
        objetivo_cpsat: objetivo da alocação do CP-SAT, medido pela enumeração.
        alocacoes_avaliadas: tamanho do espaço de busca percorrido.
        tempo_enumeracao: segundos gastos pela enumeração.
        tempo_cpsat: segundos gastos pelo solver.
        convergiu: verdadeiro quando os dois objetivos coincidem.
        observacao: motivo da divergência, quando houver.
    """

    indice: int
    quantidade_itens: int
    quantidade_mercados: int
    peso_conveniencia: float
    objetivo_enumeracao: int
    objetivo_cpsat: int
    alocacoes_avaliadas: int
    tempo_enumeracao: float
    tempo_cpsat: float
    convergiu: bool
    observacao: str


def arredondar_meio_para_cima(valor: float) -> int:
    """Arredonda para o inteiro mais próximo com o meio sempre para cima.

    Args:
        valor: número real a arredondar.

    Returns:
        O inteiro mais próximo; ``x.5`` sempre sobe.
    """
    return int(math.floor(valor + 0.5))


def candidatos_elegiveis(requisicao: RequisicaoOtimizacao) -> List[Dict[int, int]]:
    """Pares viáveis de cada item, com o custo total do item naquele mercado.

    Um candidato só é elegível se o estoque cobre a quantidade pedida — é a restrição de
    estoque suficiente, aplicada aqui de forma independente.

    Args:
        requisicao: instância a avaliar.

    Returns:
        Uma lista paralela a ``requisicao.itens``, cada posição mapeando
        ``mercado_id -> custo em centavos``.
    """
    elegiveis: List[Dict[int, int]] = []
    for item in requisicao.itens:
        opcoes: Dict[int, int] = {}
        for candidato in item.candidatos:
            if candidato.quantidade_disponivel >= item.quantidade:
                opcoes[candidato.mercado_id] = arredondar_meio_para_cima(
                    candidato.preco_unitario_centavos * item.quantidade
                )
        elegiveis.append(opcoes)
    return elegiveis


def avaliar_objetivo(
    alocacao: Sequence[Optional[int]],
    elegiveis: Sequence[Dict[int, int]],
    requisicao: RequisicaoOtimizacao,
    peso_escalado: int,
) -> int:
    """Valor da função objetivo escalarizada para uma alocação completa.

    Trabalha em inteiros escalados por :data:`ESCALA_DO_PESO` para que o peso fracionário
    não introduza ponto flutuante na comparação.

    Args:
        alocacao: mercado escolhido para cada item, na ordem dos itens; ``None`` para item
            deixado sem atendimento.
        elegiveis: pares viáveis por item, com custo.
        requisicao: instância avaliada, de onde vem o custo por visita.
        peso_escalado: ``peso_conveniencia`` multiplicado por :data:`ESCALA_DO_PESO`.

    Returns:
        O objetivo escalado, em centésimos de centavo.
    """
    custo_dos_itens = 0
    mercados_visitados = set()
    for indice, mercado_id in enumerate(alocacao):
        if mercado_id is None:
            continue
        custo_dos_itens += elegiveis[indice][mercado_id]
        mercados_visitados.add(mercado_id)

    custo_das_visitas = requisicao.custo_por_visita_centavos * len(mercados_visitados)
    return ESCALA_DO_PESO * custo_dos_itens + peso_escalado * custo_das_visitas


def resolver_por_enumeracao(
    requisicao: RequisicaoOtimizacao,
) -> Tuple[int, List[Optional[int]], int]:
    """Encontra o ótimo global percorrendo todas as atribuições possíveis.

    Itens sem nenhum candidato elegível são fixados como não atendidos: não há escolha a
    fazer para eles. Para os demais, todas as combinações de mercado são avaliadas.

    Args:
        requisicao: instância a resolver.

    Returns:
        Uma tripla ``(menor objetivo, melhor alocação, número de alocações avaliadas)``.
    """
    elegiveis = candidatos_elegiveis(requisicao)
    peso_escalado = arredondar_meio_para_cima(requisicao.peso_conveniencia * ESCALA_DO_PESO)

    opcoes_por_item: List[List[Optional[int]]] = []
    for opcoes in elegiveis:
        if opcoes:
            opcoes_por_item.append(sorted(opcoes.keys()))
        else:
            opcoes_por_item.append([None])

    melhor_objetivo: Optional[int] = None
    melhor_alocacao: List[Optional[int]] = []
    avaliadas = 0
    for combinacao in itertools.product(*opcoes_por_item):
        avaliadas += 1
        objetivo = avaliar_objetivo(combinacao, elegiveis, requisicao, peso_escalado)
        if melhor_objetivo is None or objetivo < melhor_objetivo:
            melhor_objetivo = objetivo
            melhor_alocacao = list(combinacao)

    return (melhor_objetivo or 0), melhor_alocacao, avaliadas


def alocacao_do_cpsat(resposta) -> Dict[int, int]:
    """Extrai o mapa ``item_id -> mercado_id`` da resposta do solver.

    Args:
        resposta: resposta devolvida por ``resolver_alocacao_de_compras``.

    Returns:
        O mercado escolhido para cada item atendido.
    """
    escolhas: Dict[int, int] = {}
    for compra in resposta.compras_por_mercado:
        for item in compra.itens:
            escolhas[item.item_id] = compra.mercado_id
    return escolhas


def gerar_instancia(sorteio: random.Random, indice: int) -> RequisicaoOtimizacao:
    """Sorteia uma instância pequena, mas com trade-off real.

    Os preços variam por mercado o bastante para que dividir a compra às vezes compense e
    às vezes não. Parte dos itens recebe estoque escasso ou nenhuma oferta, para que os
    caminhos de não atendimento também entrem na validação.

    Args:
        sorteio: gerador aleatório já semeado.
        indice: número da instância, usado só para rotular os itens.

    Returns:
        A requisição válida, pronta para os dois métodos de resolução.
    """
    quantidade_mercados = sorteio.randint(2, 4)
    quantidade_itens = sorteio.randint(2, 5)
    mercados = sorteio.sample(MERCADOS_DO_RECORTE, quantidade_mercados)

    itens = []
    for numero_do_item in range(1, quantidade_itens + 1):
        preco_base = sorteio.randint(300, 4000)
        quantidade = float(sorteio.choice([1, 1, 1, 2, 3]))

        candidatos = []
        for mercado_id, _, _, _ in mercados:
            if sorteio.random() < 0.15:
                continue  # o mercado não vende o item
            variacao = sorteio.uniform(0.80, 1.30)
            estoque = 0.0 if sorteio.random() < 0.08 else float(sorteio.randint(1, 12))
            candidatos.append(
                {
                    "mercado_id": mercado_id,
                    "marca_id": 500 + numero_do_item,
                    "marca_nome": "Marca %d" % numero_do_item,
                    "preco_unitario_centavos": max(1, int(preco_base * variacao)),
                    "quantidade_disponivel": estoque,
                }
            )

        itens.append(
            {
                "item_id": numero_do_item,
                "descricao": "Instancia %d - item %d" % (indice, numero_do_item),
                "quantidade": quantidade,
                "unidade": "un",
                "candidatos": candidatos,
            }
        )

    return RequisicaoOtimizacao(
        origem={"latitude": CENTRO_DE_JUAZEIRO[0], "longitude": CENTRO_DE_JUAZEIRO[1]},
        peso_conveniencia=sorteio.choice([0.0, 0.5, 1.0, 3.0]),
        custo_por_visita_centavos=800,
        mercados=[
            {
                "mercado_id": mercado_id,
                "nome": nome,
                "latitude": latitude,
                "longitude": longitude,
            }
            for mercado_id, nome, latitude, longitude in mercados
        ],
        itens=itens,
    )


def validar_instancia(requisicao: RequisicaoOtimizacao, indice: int) -> ResultadoDaInstancia:
    """Resolve a instância pelos dois métodos e compara os objetivos.

    Args:
        requisicao: instância a validar.
        indice: número sequencial, para a tabela.

    Returns:
        A linha de resultado correspondente.
    """
    inicio_enumeracao = time.perf_counter()
    objetivo_enumeracao, _, avaliadas = resolver_por_enumeracao(requisicao)
    tempo_enumeracao = time.perf_counter() - inicio_enumeracao

    inicio_cpsat = time.perf_counter()
    resposta = resolver_alocacao_de_compras(requisicao)
    tempo_cpsat = time.perf_counter() - inicio_cpsat

    elegiveis = candidatos_elegiveis(requisicao)
    peso_escalado = arredondar_meio_para_cima(requisicao.peso_conveniencia * ESCALA_DO_PESO)

    escolhas = alocacao_do_cpsat(resposta)
    alocacao: List[Optional[int]] = []
    observacao = ""
    for posicao, item in enumerate(requisicao.itens):
        mercado_id = escolhas.get(item.item_id)
        if mercado_id is not None and mercado_id not in elegiveis[posicao]:
            observacao = "CP-SAT alocou o item %d em mercado inelegivel" % item.item_id
        if mercado_id is None and elegiveis[posicao]:
            observacao = "CP-SAT deixou o item %d sem atendimento tendo candidato" % item.item_id
        alocacao.append(mercado_id)

    objetivo_cpsat = avaliar_objetivo(alocacao, elegiveis, requisicao, peso_escalado)
    convergiu = objetivo_cpsat == objetivo_enumeracao and not observacao
    if not convergiu and not observacao:
        observacao = "objetivos diferentes"

    return ResultadoDaInstancia(
        indice=indice,
        quantidade_itens=len(requisicao.itens),
        quantidade_mercados=len(requisicao.mercados),
        peso_conveniencia=requisicao.peso_conveniencia,
        objetivo_enumeracao=objetivo_enumeracao,
        objetivo_cpsat=objetivo_cpsat,
        alocacoes_avaliadas=avaliadas,
        tempo_enumeracao=tempo_enumeracao,
        tempo_cpsat=tempo_cpsat,
        convergiu=convergiu,
        observacao=observacao or "-",
    )


def montar_relatorio(resultados: Sequence[ResultadoDaInstancia], semente: int) -> str:
    """Monta a tabela de convergência em markdown.

    Args:
        resultados: linhas já calculadas.
        semente: semente usada, registrada para reprodutibilidade.

    Returns:
        O relatório completo em markdown.
    """
    convergentes = [resultado for resultado in resultados if resultado.convergiu]
    taxa = 100.0 * len(convergentes) / len(resultados) if resultados else 0.0

    linhas = [
        "# Validação por enumeração exaustiva",
        "",
        "Comparação entre o ótimo obtido por enumeração exaustiva e a solução devolvida",
        "pelo CP-SAT. Os objetivos estão em centésimos de centavo (inteiros), na",
        "escalarização descrita em `modelo/docs/formulacao-matematica.md`.",
        "",
        "| Parâmetro | Valor |",
        "|---|---|",
        "| Instâncias avaliadas | %d |" % len(resultados),
        "| Semente | %d |" % semente,
        "| Instâncias convergentes | %d |" % len(convergentes),
        "| Taxa de convergência | %.2f%% |" % taxa,
        "",
        "| # | Itens | Mercados | Peso | Objetivo (enumeração) | "
        "Objetivo (CP-SAT) | Diferença | Alocações avaliadas | "
        "Tempo enum. (s) | Tempo CP-SAT (s) | Convergiu | Observação |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for resultado in resultados:
        linhas.append(
            "| %d | %d | %d | %.1f | %d | %d | %d | %d | %.4f | %.4f | %s | %s |"
            % (
                resultado.indice,
                resultado.quantidade_itens,
                resultado.quantidade_mercados,
                resultado.peso_conveniencia,
                resultado.objetivo_enumeracao,
                resultado.objetivo_cpsat,
                resultado.objetivo_cpsat - resultado.objetivo_enumeracao,
                resultado.alocacoes_avaliadas,
                resultado.tempo_enumeracao,
                resultado.tempo_cpsat,
                "Sim" if resultado.convergiu else "NAO",
                resultado.observacao,
            )
        )

    total_enumeracao = sum(resultado.tempo_enumeracao for resultado in resultados)
    total_cpsat = sum(resultado.tempo_cpsat for resultado in resultados)
    linhas.extend(
        [
            "",
            "## Resumo",
            "",
            "- Tempo total da enumeração: %.4f s" % total_enumeracao,
            "- Tempo total do CP-SAT: %.4f s" % total_cpsat,
            "- Alocações avaliadas ao todo: %d"
            % sum(resultado.alocacoes_avaliadas for resultado in resultados),
            "",
            (
                MENSAGEM_CONVERGENCIA_TOTAL
                if len(convergentes) == len(resultados)
                else MENSAGEM_DIVERGENCIA
            ),
        ]
    )
    return "\n".join(linhas) + "\n"


def principal() -> int:
    """Ponto de entrada da linha de comando.

    Returns:
        ``0`` quando todas as instâncias convergem; ``1`` em caso de divergência, para
        que o script sirva de portão em verificação automatizada.
    """
    analisador = argparse.ArgumentParser(
        description="Valida o modelo CP-SAT por enumeração exaustiva em instâncias pequenas."
    )
    analisador.add_argument(
        "--repeticoes", type=int, default=30, help="quantidade de instâncias a gerar"
    )
    analisador.add_argument(
        "--semente", type=int, default=42, help="semente do gerador, para reprodutibilidade"
    )
    analisador.add_argument(
        "--saida", type=str, default=None, help="arquivo markdown onde gravar o relatório"
    )
    argumentos = analisador.parse_args()

    sorteio = random.Random(argumentos.semente)
    resultados = [
        validar_instancia(gerar_instancia(sorteio, indice), indice)
        for indice in range(1, argumentos.repeticoes + 1)
    ]

    relatorio = montar_relatorio(resultados, argumentos.semente)
    if argumentos.saida:
        with open(argumentos.saida, "w", encoding="utf-8") as arquivo:
            arquivo.write(relatorio)
        print("Relatorio gravado em %s" % argumentos.saida)
    else:
        print(relatorio)

    divergentes = [resultado for resultado in resultados if not resultado.convergiu]
    if divergentes:
        print("DIVERGENCIA em %d instancia(s)." % len(divergentes))
        return 1
    print("Convergencia total em %d instancia(s)." % len(resultados))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
