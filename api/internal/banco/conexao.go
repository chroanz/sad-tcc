// Package banco cuida da conexão com o PostgreSQL e da aplicação das
// migrations embutidas no binário.
package banco

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

// Conectar abre o pool de conexões e valida a conectividade com um Ping.
// Falhar aqui é fatal: a API não sobe sem banco.
func Conectar(ctx context.Context, url string) (*pgxpool.Pool, error) {
	configuracao, err := pgxpool.ParseConfig(url)
	if err != nil {
		return nil, fmt.Errorf("interpretar BANCO_URL: %w", err)
	}
	configuracao.MaxConns = 10
	configuracao.MaxConnLifetime = time.Hour
	configuracao.MaxConnIdleTime = 15 * time.Minute

	pool, err := pgxpool.NewWithConfig(ctx, configuracao)
	if err != nil {
		return nil, fmt.Errorf("abrir pool de conexões: %w", err)
	}

	contextoPing, cancelar := context.WithTimeout(ctx, 10*time.Second)
	defer cancelar()
	if err := pool.Ping(contextoPing); err != nil {
		pool.Close()
		return nil, fmt.Errorf("verificar conexão com o banco: %w", err)
	}
	return pool, nil
}
