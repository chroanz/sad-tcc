"""Gera a migration do catálogo a partir da base da cesta básica do DIEESE.

A PoC não coleta preços em supermercados: o catálogo é o da Pesquisa Nacional da Cesta
Básica de Alimentos do DIEESE (``cesta_agosto.csv``, na raiz do projeto). O escopo
geográfico é **Juazeiro do Norte/CE**. A base traz um preço médio por cidade, e cada nome de
cidade do CSV vira um **supermercado fictício dentro de Juazeiro do Norte** ("Supermercado
Fortaleza", "Supermercado Recife"...), que pratica os preços DIEESE daquela cidade. Assim
nenhum preço é inventado e a dispersão entre os supermercados é a real.

Regras de conversão:

* os supermercados são espalhados de forma determinística num raio de
  :data:`RAIO_DOS_MERCADOS_KM` do centro de Juazeiro (espiral de Vogel, na ordem do CSV).
  As localizações são fictícias e não têm relação com os preços;

* cada coluna de produto do CSV vira um produto do catálogo (a coluna "Total da Cesta" é
  ignorada). Os itens se restringem aos da cesta;
* cada produto tem **duas marcas fictícias**, porque a base do DIEESE não tem marca: a
  "tradicional" custa o preço DIEESE mais :data:`VARIACAO_MARCA`, e a "econômica" custa o
  preço DIEESE menos a mesma variação. A média das duas é o preço publicado;
* célula com ``-`` significa que a cidade não tem aquele produto na pesquisa (por exemplo,
  a Batata no Norte e no Nordeste): nenhum preço é inserido, e o produto fica indisponível
  naquele supermercado. O supermercado cuja cidade não tem nenhum preço (Macaé) existe,
  mas não oferta nada;
* a base não informa estoque: todo preço publicado entra com
  :data:`ESTOQUE_PADRAO` unidades, ou seja, disponibilidade é ter preço.

Usa apenas biblioteca padrão. O script gera texto SQL; ele nunca escreve no banco.

Uso:
    python3 dados/gerar_catalogo_dieese.py --entrada cesta_agosto.csv \\
        --saida api/migracoes/004_catalogo_dieese.sql
"""

import argparse
import csv
import math
import sys
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, NamedTuple, Optional, TextIO, Tuple

VARIACAO_MARCA = Decimal("0.08")
"""Diferença, para mais e para menos, entre as marcas fictícias e o preço do DIEESE."""

ESTOQUE_PADRAO = Decimal("1000")
"""Estoque atribuído a todo preço publicado — a base não informa estoque."""

COLETADO_EM = "2026-08-31 12:00:00-03"
"""Data de referência da pesquisa (agosto de 2026)."""

CENTRO_JUAZEIRO = (-7.2131, -39.3153)
"""Centro de Juazeiro do Norte/CE, a mesma origem padrão da API."""

RAIO_DOS_MERCADOS_KM = 6.0
"""Raio em que os supermercados fictícios são distribuídos (dentro do recorte de ~7 km)."""

KM_POR_GRAU = 111.195
"""Quilômetros por grau de latitude (raio médio terrestre)."""


class Produto(NamedTuple):
    """Como uma coluna do CSV vira produto do catálogo.

    Attributes:
        coluna: cabeçalho da coluna no CSV do DIEESE.
        nome: nome do produto no catálogo.
        categoria: agrupamento usado apenas pela interface.
        unidade: unidade a que o preço do DIEESE se refere.
        marcas: nomes fictícios da marca tradicional e da marca econômica.
    """

    coluna: str
    nome: str
    categoria: str
    unidade: str
    marcas: Tuple[str, str]


PRODUTOS: List[Produto] = [
    Produto("Carne", "Carne bovina", "Açougue", "kg", ("Boi Nobre", "Corte Bom")),
    Produto("Leite", "Leite integral", "Laticínios", "L", ("Vale Verde", "Leiteria Serrana")),
    Produto("Feijão", "Feijão", "Mercearia", "kg", ("Grão de Ouro", "Sertão Forte")),
    Produto("Arroz", "Arroz", "Mercearia", "kg", ("Campo Dourado", "Arrozal")),
    Produto("Farinha", "Farinha", "Mercearia", "kg", ("Moinho Real", "Farinheira do Vale")),
    Produto("Batata", "Batata", "Hortifruti", "kg", ("Horta Viva", "Terra Boa")),
    Produto("Tomate", "Tomate", "Hortifruti", "kg", ("Horta Viva", "Terra Boa")),
    Produto("Pão", "Pão francês", "Padaria", "kg", ("Trigal", "Forno Bom")),
    Produto("Café", "Café em pó", "Mercearia", "kg", ("Serra Alta", "Grão Torrado")),
    Produto("Banana", "Banana (dúzia)", "Hortifruti", "un", ("Horta Viva", "Terra Boa")),
    Produto("Açúcar", "Açúcar", "Mercearia", "kg", ("Doce Lar", "Canavial")),
    Produto("Óleo", "Óleo de soja (900 ml)", "Mercearia", "un", ("Soja Pura", "Óleo Bom")),
    Produto("Manteiga", "Manteiga", "Laticínios", "kg", ("Vale Verde", "Leiteria Serrana")),
]

# UF de cada cidade do CSV, usada só no endereço do supermercado homônimo.
UF_DAS_CIDADES: Dict[str, str] = {
    "Brasília": "DF",
    "Campo Grande": "MS",
    "Cuiabá": "MT",
    "Goiânia": "GO",
    "Belo Horizonte": "MG",
    "Rio de Janeiro": "RJ",
    "São Paulo": "SP",
    "Vitória": "ES",
    "Curitiba": "PR",
    "Florianópolis": "SC",
    "Porto Alegre": "RS",
    "Belém": "PA",
    "Boa Vista": "RR",
    "Macapá": "AP",
    "Manaus": "AM",
    "Palmas": "TO",
    "Porto Velho": "RO",
    "Rio Branco": "AC",
    "Aracaju": "SE",
    "Fortaleza": "CE",
    "João Pessoa": "PB",
    "Maceió": "AL",
    "Natal": "RN",
    "Recife": "PE",
    "Salvador": "BA",
    "São Luís": "MA",
    "Teresina": "PI",
    "Macaé": "RJ",
}


class Cidade(NamedTuple):
    """Uma linha do CSV já interpretada.

    Attributes:
        nome: nome da cidade, como no CSV.
        precos: preço DIEESE de cada produto (pela coluna); ``None`` quando a célula é ``-``.
    """

    nome: str
    precos: Dict[str, Optional[Decimal]]


def ler_preco(bruto: str) -> Optional[Decimal]:
    """Converte uma célula do CSV (``"45,31"`` ou ``"-"``) em reais.

    Args:
        bruto: texto da célula.

    Returns:
        O preço, ou ``None`` quando a cidade não tem o produto na pesquisa.

    Raises:
        ValueError: quando a célula não é nem um número nem ``-``.
    """
    texto = bruto.strip()
    if texto in ("", "-"):
        return None
    preco = Decimal(texto.replace(".", "").replace(",", "."))
    if preco <= 0:
        raise ValueError("preço não positivo: %r" % bruto)
    return preco


def ler_cesta(caminho: str) -> List[Cidade]:
    """Lê o CSV do DIEESE.

    Args:
        caminho: caminho do arquivo.

    Returns:
        As cidades na ordem do arquivo.

    Raises:
        ValueError: quando falta coluna, a cidade não tem coordenada ou a célula é inválida.
    """
    with open(caminho, newline="", encoding="utf-8-sig") as arquivo:
        leitor = csv.DictReader(arquivo)
        cabecalho = leitor.fieldnames or []
        faltando = [p.coluna for p in PRODUTOS if p.coluna not in cabecalho]
        if faltando or "Cidade" not in cabecalho:
            raise ValueError("colunas ausentes no CSV: %s" % (faltando or ["Cidade"]))

        cidades = []
        for numero, linha in enumerate(leitor, start=2):
            nome = linha["Cidade"].strip()
            if nome not in UF_DAS_CIDADES:
                raise ValueError("linha %d: cidade sem UF cadastrada: %r" % (numero, nome))
            try:
                precos = {p.coluna: ler_preco(linha[p.coluna] or "") for p in PRODUTOS}
            except ValueError as erro:
                raise ValueError("linha %d (%s): %s" % (numero, nome, erro)) from erro
            cidades.append(Cidade(nome, precos))
    return cidades


def preco_da_marca(preco_dieese: Decimal, fator: Decimal) -> Decimal:
    """Aplica a variação da marca ao preço do DIEESE, com duas casas, meio para cima."""
    return (preco_dieese * fator).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def texto_sql(valor: str) -> str:
    """Literal SQL de texto, com aspas simples escapadas."""
    return "'" + valor.replace("'", "''") + "'"


def nome_do_mercado(cidade: str) -> str:
    """Nome do supermercado fictício de Juazeiro que pratica os preços da cidade."""
    return "Supermercado %s" % cidade


def posicionar_mercados(quantidade: int) -> List[Tuple[float, float]]:
    """Espalha os supermercados pela cidade numa espiral de Vogel.

    O ``k``-ésimo ponto fica a ``R·√((k+0,5)/n)`` do centro, girado ``k`` vezes o ângulo de
    ouro. A distribuição é uniforme no disco e determinística: gerar de novo produz as
    mesmas coordenadas.

    Args:
        quantidade: número de supermercados.

    Returns:
        ``(latitude, longitude)`` de cada supermercado, na ordem pedida.
    """
    angulo_de_ouro = math.pi * (3.0 - math.sqrt(5.0))
    latitude_centro, longitude_centro = CENTRO_JUAZEIRO
    km_por_grau_de_longitude = KM_POR_GRAU * math.cos(math.radians(latitude_centro))
    pontos = []
    for k in range(quantidade):
        raio = RAIO_DOS_MERCADOS_KM * math.sqrt((k + 0.5) / quantidade)
        angulo = k * angulo_de_ouro
        pontos.append(
            (
                round(latitude_centro + raio * math.sin(angulo) / KM_POR_GRAU, 6),
                round(longitude_centro + raio * math.cos(angulo) / km_por_grau_de_longitude, 6),
            )
        )
    return pontos


def escrever_sql(cidades: List[Cidade], entrada: str, saida: TextIO) -> None:
    """Escreve a migration completa.

    Args:
        cidades: linhas do CSV já interpretadas.
        entrada: nome do CSV, registrado no cabeçalho do SQL.
        saida: arquivo aberto para escrita.
    """
    sem_dados = [c.nome for c in cidades if all(v is None for v in c.precos.values())]
    quantidade_precos = 2 * sum(
        1 for c in cidades for valor in c.precos.values() if valor is not None
    )

    escrever = saida.write
    escrever(
        "-- =============================================================================\n"
        "-- Migration 004 — Catálogo da cesta básica do DIEESE\n"
        "--\n"
        "-- GERADO por dados/gerar_catalogo_dieese.py a partir de %s.\n"
        "-- Não edite à mão: altere o CSV ou o gerador e gere de novo.\n"
        "--\n"
        "-- Substitui o catálogo fictício de 002 (preços inventados) pelos preços\n"
        "-- médios da Pesquisa Nacional da Cesta Básica do DIEESE, agosto de 2026.\n"
        "-- O escopo é Juazeiro do Norte/CE:\n"
        "--   * cada nome de cidade do CSV vira um supermercado FICTÍCIO dentro de\n"
        "--     Juazeiro do Norte, com os preços DIEESE daquela cidade (%d no total);\n"
        "--   * as localizações são fictícias: espiral determinística num raio de\n"
        "--     %s km do centro, sem relação com os preços;\n"
        "--   * os produtos são os %d itens da cesta, e só eles;\n"
        "--   * cada produto tem duas marcas FICTÍCIAS: a primeira custa o preço DIEESE\n"
        "--     +%s%%, a segunda -%s%% (a média das duas é o preço publicado);\n"
        '--   * célula "-" no CSV = produto indisponível naquela cidade (sem preço);\n'
        "--   * a base não informa estoque: todo preço entra com %s unidades.\n"
        "%s"
        "--\n"
        "-- O catálogo anterior era todo fictício e é removido — junto com tudo que\n"
        "-- dependia dele (itens de lista e recomendações). As contas de usuário são\n"
        "-- preservadas. Sem BEGIN/COMMIT: o runner aplica cada arquivo numa transação.\n"
        "-- =============================================================================\n\n"
        % (
            entrada,
            len(cidades),
            RAIO_DOS_MERCADOS_KM,
            len(PRODUTOS),
            (VARIACAO_MARCA * 100).normalize(),
            (VARIACAO_MARCA * 100).normalize(),
            ESTOQUE_PADRAO,
            (
                "--   * sem nenhum preço na pesquisa (o supermercado existe, mas não\n"
                "--     oferta nada): %s.\n" % ", ".join(sem_dados)
                if sem_dados
                else ""
            ),
        )
    )

    escrever(
        "-- 1. Remove o catálogo fictício e o que dependia dele.\n"
        "DELETE FROM recomendacoes;\n"
        "DELETE FROM itens_lista;\n"
        "DELETE FROM precos;\n"
        "DELETE FROM marcas;\n"
        "DELETE FROM produtos;\n"
        "DELETE FROM mercados;\n"
        "DELETE FROM listas_compra\n"
        " WHERE usuario_id IN (SELECT id FROM usuarios WHERE email = 'demo@exemplo.com');\n\n"
    )

    escrever(
        "COMMENT ON COLUMN mercados.latitude  IS 'Latitude em graus decimais (WGS84); "
        "usada no cálculo de distância em linha reta feito na aplicação.';\n"
        "COMMENT ON COLUMN mercados.longitude IS 'Longitude em graus decimais (WGS84); "
        "usada no cálculo de distância em linha reta feito na aplicação.';\n\n"
    )

    escrever("-- 2. Supermercados: um por nome de cidade do CSV, todos em Juazeiro do Norte.\n")
    escrever("INSERT INTO mercados (nome, latitude, longitude, endereco)\nVALUES\n")
    linhas = []
    for cidade, (latitude, longitude) in zip(
        cidades, posicionar_mercados(len(cidades)), strict=True
    ):
        linhas.append(
            "    (%s, %.6f, %.6f, %s)"
            % (
                texto_sql(nome_do_mercado(cidade.nome)),
                latitude,
                longitude,
                texto_sql(
                    "Juazeiro do Norte/CE (localização fictícia) — preços da cesta "
                    "DIEESE de %s/%s" % (cidade.nome, UF_DAS_CIDADES[cidade.nome])
                ),
            )
        )
    escrever(",\n".join(linhas) + ";\n\n")

    escrever("-- 3. Produtos: os itens da cesta básica.\n")
    escrever("INSERT INTO produtos (nome, categoria)\nVALUES\n")
    escrever(
        ",\n".join("    (%s, %s)" % (texto_sql(p.nome), texto_sql(p.categoria)) for p in PRODUTOS)
        + ";\n\n"
    )

    escrever("-- 4. Marcas fictícias: duas por produto.\n")
    escrever(
        "INSERT INTO marcas (produto_id, nome)\n"
        "SELECT p.id, d.marca\n"
        "  FROM (\n"
        "      VALUES\n"
    )
    escrever(
        ",\n".join(
            "          (%s, %s)" % (texto_sql(p.nome), texto_sql(marca))
            for p in PRODUTOS
            for marca in p.marcas
        )
        + "\n  ) AS d(produto, marca)\n  JOIN produtos p ON p.nome = d.produto;\n\n"
    )

    escrever("-- 5. Preços: %d snapshots, dois por célula preenchida do CSV.\n" % quantidade_precos)
    escrever(
        "WITH dados (mercado_nome, produto_nome, marca_nome, preco, unidade) AS (\n" "    VALUES\n"
    )
    fatores = (Decimal(1) + VARIACAO_MARCA, Decimal(1) - VARIACAO_MARCA)
    linhas = []
    for cidade in cidades:
        for produto in PRODUTOS:
            preco_dieese = cidade.precos[produto.coluna]
            if preco_dieese is None:
                continue
            for marca, fator in zip(produto.marcas, fatores, strict=True):
                linhas.append(
                    "        (%s, %s, %s, %s::numeric(10,2), %s)"
                    % (
                        texto_sql(nome_do_mercado(cidade.nome)),
                        texto_sql(produto.nome),
                        texto_sql(marca),
                        preco_da_marca(preco_dieese, fator),
                        texto_sql(produto.unidade),
                    )
                )
    escrever(",\n".join(linhas) + "\n)\n")
    escrever(
        "INSERT INTO precos (marca_id, mercado_id, preco, unidade, "
        "quantidade_disponivel, coletado_em)\n"
        "SELECT ma.id, me.id, d.preco, d.unidade, %s, %s::timestamptz\n"
        "  FROM dados d\n"
        "  JOIN mercados me ON me.nome = d.mercado_nome\n"
        "  JOIN produtos pr ON pr.nome = d.produto_nome\n"
        "  JOIN marcas   ma ON ma.produto_id = pr.id AND ma.nome = d.marca_nome;\n\n"
        % (ESTOQUE_PADRAO, texto_sql(COLETADO_EM))
    )

    escrever(
        "-- 6. Lista de demonstração: a cesta inteira, com marca livre\n"
        "--    (marca_id NULL deixa o otimizador escolher qualquer marca).\n"
        "INSERT INTO listas_compra (usuario_id, nome)\n"
        "SELECT id, 'Cesta básica do mês' FROM usuarios WHERE email = 'demo@exemplo.com';\n\n"
        "INSERT INTO itens_lista (lista_id, produto_id, marca_id, quantidade, unidade)\n"
        "SELECT l.id, p.id, NULL, d.quantidade, d.unidade\n"
        "  FROM (\n"
        "      VALUES\n"
    )
    quantidades = {"Carne bovina": "2", "Leite integral": "6", "Feijão": "2", "Arroz": "5"}
    escrever(
        ",\n".join(
            "          (%s, %s::numeric(12,3), %s)"
            % (texto_sql(p.nome), quantidades.get(p.nome, "1"), texto_sql(p.unidade))
            for p in PRODUTOS
        )
        + "\n  ) AS d(produto_nome, quantidade, unidade)\n"
        "  JOIN usuarios      u ON u.email = 'demo@exemplo.com'\n"
        "  JOIN listas_compra l ON l.usuario_id = u.id AND l.nome = 'Cesta básica do mês'\n"
        "  JOIN produtos      p ON p.nome = d.produto_nome;\n"
    )


def principal() -> int:
    """Ponto de entrada da linha de comando.

    Returns:
        ``0`` em caso de sucesso; ``1`` quando o CSV é inválido.
    """
    analisador = argparse.ArgumentParser(
        description="Gera a migration do catálogo a partir do CSV da cesta básica do DIEESE."
    )
    analisador.add_argument("--entrada", required=True, help="CSV do DIEESE")
    analisador.add_argument("--saida", help="arquivo SQL a gerar; sem ele, escreve na saída padrão")
    argumentos = analisador.parse_args()

    try:
        cidades = ler_cesta(argumentos.entrada)
    except (IOError, ValueError) as falha:
        print("Não foi possível ler %s: %s" % (argumentos.entrada, falha), file=sys.stderr)
        return 1

    if argumentos.saida:
        with open(argumentos.saida, "w", encoding="utf-8") as arquivo:
            escrever_sql(cidades, argumentos.entrada, arquivo)
        print("SQL gravado em %s." % argumentos.saida)
    else:
        escrever_sql(cidades, argumentos.entrada, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
