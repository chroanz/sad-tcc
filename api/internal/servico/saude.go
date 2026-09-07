package servico

import (
	"context"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/tcc/sad-compras/api/internal/otimizador"
)

// Saude verifica as dependências externas da API.
type Saude struct {
	pool    *pgxpool.Pool
	cliente *otimizador.Cliente
}

// RelatorioSaude é o corpo de GET /saude.
type RelatorioSaude struct {
	Status     string `json:"status"`
	Banco      string `json:"banco"`
	Otimizador string `json:"otimizador"`
}

// NovaSaude monta o verificador.
func NovaSaude(pool *pgxpool.Pool, cliente *otimizador.Cliente) *Saude {
	return &Saude{pool: pool, cliente: cliente}
}

// Verificar consulta banco e otimizador. O status geral só é "ok" quando as
// duas dependências respondem: sem o otimizador a API continua servindo CRUD,
// mas não consegue gerar recomendação.
func (s *Saude) Verificar(ctx context.Context) RelatorioSaude {
	relatorio := RelatorioSaude{Status: "ok", Banco: "ok", Otimizador: "ok"}

	if err := s.pool.Ping(ctx); err != nil {
		relatorio.Banco = "indisponivel"
		relatorio.Status = "degradado"
	}
	if err := s.cliente.Saude(ctx); err != nil {
		relatorio.Otimizador = "indisponivel"
		relatorio.Status = "degradado"
	}
	return relatorio
}
