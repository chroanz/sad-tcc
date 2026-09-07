// Comando servidor sobe a API REST do Sistema de Apoio à Decisão para compras
// de supermercado.
//
// Este arquivo é só composição: lê a configuração, abre o pool, aplica as
// migrations, monta os serviços e liga o roteador. Nenhuma regra de negócio
// mora aqui.
package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/tcc/sad-compras/api/internal/banco"
	"github.com/tcc/sad-compras/api/internal/configuracao"
	"github.com/tcc/sad-compras/api/internal/otimizador"
	"github.com/tcc/sad-compras/api/internal/repositorio"
	"github.com/tcc/sad-compras/api/internal/servico"
	"github.com/tcc/sad-compras/api/internal/transporte"
)

// prazoEncerramento é quanto o servidor espera as requisições em andamento
// terminarem antes de encerrar à força.
const prazoEncerramento = 10 * time.Second

func main() {
	registro := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	}))

	if err := executar(registro); err != nil {
		registro.Error("falha ao executar o servidor", "erro", err)
		os.Exit(1)
	}
}

func executar(registro *slog.Logger) error {
	config, err := configuracao.Carregar()
	if err != nil {
		return err
	}

	ctx, cancelar := context.WithCancel(context.Background())
	defer cancelar()

	pool, err := banco.Conectar(ctx, config.BancoURL)
	if err != nil {
		return err
	}
	defer pool.Close()
	registro.Info("conectado ao PostgreSQL")

	if config.AplicarMigracoes {
		if err := banco.AplicarMigracoes(ctx, pool, registro); err != nil {
			return err
		}
	} else if err := banco.Verificar(ctx, pool); err != nil {
		return err
	}

	clienteOtimizador := otimizador.NovoCliente(
		config.OtimizadorURL, config.OtimizadorTempoLimite)

	repo := repositorio.Novo(pool)
	servicoLista := servico.NovaLista(repo)
	deps := transporte.Dependencias{
		Autenticacao: servico.NovaAutenticacao(repo, config.JWTSegredo, config.JWTValidade),
		Catalogo:     servico.NovoCatalogo(repo),
		Lista:        servicoLista,
		Recomendacao: servico.NovaRecomendacao(
			repo, servicoLista, clienteOtimizador,
			config.OrigemPadraoLatitude, config.OrigemPadraoLongitude),
		Saude: servico.NovaSaude(pool, clienteOtimizador),
	}

	servidor := &http.Server{
		Addr:              ":" + config.PortaAPI,
		Handler:           transporte.MontarRoteador(deps),
		ReadHeaderTimeout: 10 * time.Second,
	}

	falhas := make(chan error, 1)
	go func() {
		registro.Info("API ouvindo", "porta", config.PortaAPI)
		if err := servidor.ListenAndServe(); err != nil &&
			!errors.Is(err, http.ErrServerClosed) {
			falhas <- err
		}
	}()

	sinais := make(chan os.Signal, 1)
	signal.Notify(sinais, os.Interrupt, syscall.SIGTERM)

	select {
	case err := <-falhas:
		return err
	case sinal := <-sinais:
		registro.Info("encerrando", "sinal", sinal.String())
	}

	prazo, cancelarPrazo := context.WithTimeout(context.Background(), prazoEncerramento)
	defer cancelarPrazo()
	return servidor.Shutdown(prazo)
}
