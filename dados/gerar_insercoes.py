"""Converte a planilha de coleta manual de precos em comandos SQL de insercao.

Existe para que a coleta semanal em Juazeiro do Norte nao precise ser digitada como
INSERT a mao — o maior risco de atraso do projeto, segundo o `plano_desenvolvimento.md`,
e a coleta de precos, e tudo que a torne mais rapida mitiga esse risco.

Usa apenas biblioteca padrao: nao ha driver de banco nem dependencia externa. O script
gera texto SQL, que o autor revisa antes de aplicar.

As chaves estrangeiras sao resolvidas por subconsulta a partir dos nomes, porque as PKs
sao BIGSERIAL e nao podem ser fixadas no arquivo.

Uso:
    python dados/gerar_insercoes.py --entrada dados/coleta/coleta_2026-09-01.csv --verificar
    python dados/gerar_insercoes.py --entrada dados/coleta/coleta_2026-09-01.csv --saida coleta.sql
"""

import argparse
import csv
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, NamedTuple, Sequence, TextIO

COLUNAS_ESPERADAS = [
    "mercado",
    "produto",
    "marca",
    "preco",
    "unidade",
    "quantidade_disponivel",
    "coletado_em",
]

# Espelha o CHECK de `precos.unidade` no esquema.
UNIDADES_VALIDAS = ("kg", "g", "L", "ml", "un")


class LinhaDeColeta(NamedTuple):
    """Uma observacao de preco pronta para virar INSERT.

    Attributes:
        numero_da_linha: posicao no CSV, usada nas mensagens de erro.
        mercado: nome exato do mercado, como cadastrado em `mercados.nome`.
        produto: nome exato do produto, como cadastrado em `produtos.nome`.
        marca: nome exato da marca, como cadastrado em `marcas.nome`.
        preco: valor observado, com duas casas decimais.
        unidade: unidade da embalagem.
        quantidade_disponivel: estoque observado; zero significa em falta.
        coletado_em: data da observacao, no formato ISO.
    """

    numero_da_linha: int
    mercado: str
    produto: str
    marca: str
    preco: Decimal
    unidade: str
    quantidade_disponivel: Decimal
    coletado_em: str


class ErroDeValidacao(NamedTuple):
    """Um problema encontrado em uma linha do CSV.

    Attributes:
        numero_da_linha: posicao no CSV.
        coluna: nome da coluna problematica.
        mensagem: descricao do problema.
    """

    numero_da_linha: int
    coluna: str
    mensagem: str


def escapar_texto(valor: str) -> str:
    """Escapa aspas simples para interpolacao segura em literal SQL.

    Args:
        valor: texto a inserir no SQL.

    Returns:
        O texto com aspas simples duplicadas.
    """
    return valor.replace("'", "''")


def validar_linha(
    numero_da_linha: int, bruta: dict
) -> "tuple[LinhaDeColeta, List[ErroDeValidacao]]":
    """Valida uma linha do CSV e a converte em :class:`LinhaDeColeta`.

    Acusa a linha e a coluna de cada problema, em vez de gerar SQL invalido que so
    falharia no banco.

    Args:
        numero_da_linha: posicao da linha no arquivo, contando o cabecalho.
        bruta: dicionario devolvido pelo ``csv.DictReader``.

    Returns:
        A linha convertida e a lista de erros encontrados. Havendo erros, a linha
        devolvida nao deve ser usada.
    """
    erros: List[ErroDeValidacao] = []

    def texto_obrigatorio(coluna: str) -> str:
        valor = (bruta.get(coluna) or "").strip()
        if not valor:
            erros.append(ErroDeValidacao(numero_da_linha, coluna, "valor obrigatorio vazio"))
        return valor

    mercado = texto_obrigatorio("mercado")
    produto = texto_obrigatorio("produto")
    marca = texto_obrigatorio("marca")

    preco = Decimal("0")
    bruto_preco = (bruta.get("preco") or "").strip().replace(",", ".")
    try:
        preco = Decimal(bruto_preco)
        if preco <= 0:
            erros.append(ErroDeValidacao(numero_da_linha, "preco", "preco deve ser maior que zero"))
    except (InvalidOperation, ValueError):
        erros.append(
            ErroDeValidacao(numero_da_linha, "preco", "preco nao numerico: %r" % bruto_preco)
        )

    unidade = (bruta.get("unidade") or "").strip()
    if unidade not in UNIDADES_VALIDAS:
        erros.append(
            ErroDeValidacao(
                numero_da_linha,
                "unidade",
                "unidade %r fora da lista permitida %s" % (unidade, list(UNIDADES_VALIDAS)),
            )
        )

    quantidade = Decimal("0")
    bruta_quantidade = (bruta.get("quantidade_disponivel") or "").strip().replace(",", ".")
    try:
        quantidade = Decimal(bruta_quantidade)
        if quantidade < 0:
            erros.append(
                ErroDeValidacao(
                    numero_da_linha,
                    "quantidade_disponivel",
                    "quantidade nao pode ser negativa",
                )
            )
    except (InvalidOperation, ValueError):
        erros.append(
            ErroDeValidacao(
                numero_da_linha,
                "quantidade_disponivel",
                "quantidade nao numerica: %r" % bruta_quantidade,
            )
        )

    coletado_em = (bruta.get("coletado_em") or "").strip()
    try:
        datetime.strptime(coletado_em[:10], "%Y-%m-%d")
    except ValueError:
        erros.append(
            ErroDeValidacao(
                numero_da_linha,
                "coletado_em",
                "data invalida %r; use o formato AAAA-MM-DD" % coletado_em,
            )
        )

    linha = LinhaDeColeta(
        numero_da_linha=numero_da_linha,
        mercado=mercado,
        produto=produto,
        marca=marca,
        preco=preco,
        unidade=unidade,
        quantidade_disponivel=quantidade,
        coletado_em=coletado_em,
    )
    return linha, erros


def ler_coleta(caminho: str) -> "tuple[List[LinhaDeColeta], List[ErroDeValidacao]]":
    """Le e valida o arquivo de coleta inteiro.

    Args:
        caminho: caminho do CSV.

    Returns:
        As linhas validas e todos os erros encontrados.
    """
    linhas: List[LinhaDeColeta] = []
    erros: List[ErroDeValidacao] = []

    with open(caminho, newline="", encoding="utf-8-sig") as arquivo:
        leitor = csv.DictReader(arquivo)
        cabecalho = leitor.fieldnames or []

        faltando = [coluna for coluna in COLUNAS_ESPERADAS if coluna not in cabecalho]
        if faltando:
            erros.append(
                ErroDeValidacao(1, ",".join(faltando), "colunas ausentes no cabecalho")
            )
            return linhas, erros

        for numero, bruta in enumerate(leitor, start=2):
            linha, erros_da_linha = validar_linha(numero, bruta)
            if erros_da_linha:
                erros.extend(erros_da_linha)
            else:
                linhas.append(linha)

    return linhas, erros


def escrever_sql(linhas: Sequence[LinhaDeColeta], saida: TextIO) -> None:
    """Escreve os comandos INSERT correspondentes as linhas validadas.

    Cada INSERT resolve `marca_id` e `mercado_id` por subconsulta pelos nomes, e o
    `WHERE NOT EXISTS` impede duplicar a mesma observacao caso o script seja aplicado
    duas vezes.

    Args:
        linhas: observacoes ja validadas.
        saida: arquivo aberto para escrita.
    """
    saida.write("-- Gerado por dados/gerar_insercoes.py. Revise antes de aplicar.\n")
    saida.write("-- `precos` e append-only: estas linhas apenas acrescentam snapshots.\n\n")

    for linha in linhas:
        saida.write(
            "INSERT INTO precos (marca_id, mercado_id, preco, unidade, "
            "quantidade_disponivel, coletado_em)\n"
            "SELECT ma.id, me.id, %s::numeric, '%s', %s::numeric, '%s'::timestamptz\n"
            "  FROM marcas ma\n"
            "  JOIN produtos p ON p.id = ma.produto_id AND p.nome = '%s'\n"
            "  CROSS JOIN mercados me\n"
            " WHERE ma.nome = '%s' AND me.nome = '%s'\n"
            "   AND NOT EXISTS (\n"
            "       SELECT 1 FROM precos pr\n"
            "        WHERE pr.marca_id = ma.id AND pr.mercado_id = me.id\n"
            "          AND pr.coletado_em = '%s'::timestamptz\n"
            "   );\n\n"
            % (
                linha.preco,
                escapar_texto(linha.unidade),
                linha.quantidade_disponivel,
                escapar_texto(linha.coletado_em),
                escapar_texto(linha.produto),
                escapar_texto(linha.marca),
                escapar_texto(linha.mercado),
                escapar_texto(linha.coletado_em),
            )
        )


def principal() -> int:
    """Ponto de entrada da linha de comando.

    Returns:
        ``0`` quando tudo e valido; ``1`` quando ha erro de validacao.
    """
    analisador = argparse.ArgumentParser(
        description="Converte a planilha de coleta manual de precos em SQL de insercao."
    )
    analisador.add_argument("--entrada", required=True, help="arquivo CSV da coleta")
    analisador.add_argument("--saida", help="arquivo SQL a gerar; sem ele, escreve na saida padrao")
    analisador.add_argument(
        "--verificar",
        action="store_true",
        help="apenas valida o CSV, sem gerar SQL",
    )
    argumentos = analisador.parse_args()

    try:
        linhas, erros = ler_coleta(argumentos.entrada)
    except IOError as falha:
        print("Nao foi possivel ler %s: %s" % (argumentos.entrada, falha), file=sys.stderr)
        return 1

    if erros:
        print("%d problema(s) encontrado(s):" % len(erros), file=sys.stderr)
        for erro in erros:
            print(
                "  linha %d, coluna %s: %s" % (erro.numero_da_linha, erro.coluna, erro.mensagem),
                file=sys.stderr,
            )
        return 1

    print("%d linha(s) valida(s) em %s." % (len(linhas), argumentos.entrada))

    if argumentos.verificar:
        return 0

    if argumentos.saida:
        with open(argumentos.saida, "w", encoding="utf-8") as arquivo:
            escrever_sql(linhas, arquivo)
        print("SQL gravado em %s." % argumentos.saida)
    else:
        escrever_sql(linhas, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
