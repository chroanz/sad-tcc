// Package repositorio concentra todo o acesso SQL ao PostgreSQL. É a única
// camada que conhece nomes de tabela e de coluna; serviços trabalham apenas com
// os tipos de dominio.
//
// Valores monetários são lidos com cast explícito para texto (`preco::text`) e
// convertidos por dominio.ConverterReaisParaCentavos. Ler NUMERIC como float64
// introduziria erro de arredondamento em dinheiro, o que o contrato proíbe.
package repositorio

import (
	"errors"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/tcc/sad-compras/api/internal/dominio"
)

// codigoViolacaoUnicidade é o SQLSTATE de unique_violation no PostgreSQL.
const codigoViolacaoUnicidade = "23505"

// Repositorio agrupa as consultas sobre o pool de conexões.
type Repositorio struct {
	pool *pgxpool.Pool
}

// Novo cria o repositório sobre um pool já conectado.
func Novo(pool *pgxpool.Pool) *Repositorio {
	return &Repositorio{pool: pool}
}

// traduzirErro converte erros do driver em erros de domínio. Sem isso, cada
// serviço precisaria conhecer códigos SQLSTATE para produzir a resposta HTTP
// correta.
func traduzirErro(err error, mensagemConflito string) error {
	if err == nil {
		return nil
	}
	if errors.Is(err, pgx.ErrNoRows) {
		return dominio.ErrNaoEncontrado
	}
	var erroPostgres *pgconn.PgError
	if errors.As(err, &erroPostgres) && erroPostgres.Code == codigoViolacaoUnicidade {
		return dominio.NovoErroConflito("%s", mensagemConflito)
	}
	return err
}
