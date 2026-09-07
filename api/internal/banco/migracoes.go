package banco

import (
	"context"
	"fmt"
	"io/fs"
	"log/slog"
	"sort"
	"strings"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/tcc/sad-compras/api/migracoes"
)

const criarTabelaControle = `
CREATE TABLE IF NOT EXISTS migracoes_aplicadas (
    nome        TEXT        PRIMARY KEY,
    aplicada_em TIMESTAMPTZ NOT NULL DEFAULT now()
)`

// AplicarMigracoes executa, em ordem alfabética, todos os arquivos .sql
// embutidos em migracoes/ que ainda não constam em migracoes_aplicadas.
//
// Cada arquivo roda dentro de uma transação própria: ou o script inteiro entra
// e o nome é registrado, ou nada é aplicado. Um arquivo já registrado nunca é
// reaplicado, mesmo que seu conteúdo mude — a correção de uma migration já
// aplicada é sempre uma migration nova.
func AplicarMigracoes(ctx context.Context, pool *pgxpool.Pool, registro *slog.Logger) error {
	if _, err := pool.Exec(ctx, criarTabelaControle); err != nil {
		return fmt.Errorf("criar tabela migracoes_aplicadas: %w", err)
	}

	aplicadas, err := carregarAplicadas(ctx, pool)
	if err != nil {
		return err
	}

	nomes, err := listarArquivos()
	if err != nil {
		return err
	}

	for _, nome := range nomes {
		if aplicadas[nome] {
			registro.Debug("migration já aplicada", "arquivo", nome)
			continue
		}
		conteudo, err := migracoes.Arquivos.ReadFile(nome)
		if err != nil {
			return fmt.Errorf("ler migration %s: %w", nome, err)
		}
		if err := aplicarUma(ctx, pool, nome, string(conteudo)); err != nil {
			return err
		}
		registro.Info("migration aplicada", "arquivo", nome)
	}
	return nil
}

func aplicarUma(ctx context.Context, pool *pgxpool.Pool, nome, conteudo string) error {
	transacao, err := pool.Begin(ctx)
	if err != nil {
		return fmt.Errorf("iniciar transação da migration %s: %w", nome, err)
	}
	defer func() {
		_ = transacao.Rollback(ctx)
	}()

	if _, err := transacao.Exec(ctx, conteudo); err != nil {
		return fmt.Errorf("executar migration %s: %w", nome, err)
	}
	const registrar = `INSERT INTO migracoes_aplicadas (nome) VALUES ($1)`
	if _, err := transacao.Exec(ctx, registrar, nome); err != nil {
		return fmt.Errorf("registrar migration %s: %w", nome, err)
	}
	if err := transacao.Commit(ctx); err != nil {
		return fmt.Errorf("confirmar migration %s: %w", nome, err)
	}
	return nil
}

func carregarAplicadas(ctx context.Context, pool *pgxpool.Pool) (map[string]bool, error) {
	linhas, err := pool.Query(ctx, `SELECT nome FROM migracoes_aplicadas`)
	if err != nil {
		return nil, fmt.Errorf("consultar migrations aplicadas: %w", err)
	}
	defer linhas.Close()

	aplicadas := make(map[string]bool)
	for linhas.Next() {
		var nome string
		if err := linhas.Scan(&nome); err != nil {
			return nil, fmt.Errorf("ler nome de migration aplicada: %w", err)
		}
		aplicadas[nome] = true
	}
	if err := linhas.Err(); err != nil {
		return nil, fmt.Errorf("iterar migrations aplicadas: %w", err)
	}
	return aplicadas, nil
}

// listarArquivos devolve os nomes dos scripts .sql embutidos, em ordem
// alfabética — a ordem que define a sequência de aplicação.
func listarArquivos() ([]string, error) {
	entradas, err := fs.ReadDir(migracoes.Arquivos, ".")
	if err != nil {
		return nil, fmt.Errorf("listar migrations embutidas: %w", err)
	}
	var nomes []string
	for _, entrada := range entradas {
		if entrada.IsDir() || !strings.HasSuffix(entrada.Name(), ".sql") {
			continue
		}
		nomes = append(nomes, entrada.Name())
	}
	sort.Strings(nomes)
	return nomes, nil
}

// Verificar confirma que o banco responde. Usado pelo endpoint GET /saude.
func Verificar(ctx context.Context, pool *pgxpool.Pool) error {
	if err := pool.Ping(ctx); err != nil {
		return fmt.Errorf("ping no banco: %w", err)
	}
	return nil
}
