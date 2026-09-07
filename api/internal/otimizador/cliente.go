package otimizador

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/tcc/sad-compras/api/internal/dominio"
)

// limiteCorpoErro evita despejar no log uma resposta de erro arbitrariamente
// grande do serviço Python.
const limiteCorpoErro = 2048

// Cliente fala com o serviço Python de otimização. É seguro para uso
// concorrente: o http.Client interno já é.
type Cliente struct {
	urlBase string
	http    *http.Client
}

// NovoCliente monta o cliente com o timeout total de cada requisição.
func NovoCliente(urlBase string, tempoLimite time.Duration) *Cliente {
	return &Cliente{
		urlBase: urlBase,
		http:    &http.Client{Timeout: tempoLimite},
	}
}

// Otimizar envia o payload montado e devolve a alocação ótima.
//
// Timeout, conexão recusada e respostas 5xx viram dominio.ErrOtimizadorIndisponivel,
// que a camada de transporte traduz para 503 OTIMIZADOR_INDISPONIVEL. Um 422
// significa payload inválido — ou seja, defeito na montagem feita pela API — e
// por isso é tratado como erro interno, nunca como indisponibilidade.
func (c *Cliente) Otimizar(ctx context.Context, requisicao Requisicao) (Resposta, error) {
	corpo, err := json.Marshal(requisicao)
	if err != nil {
		return Resposta{}, fmt.Errorf("serializar requisição de otimização: %w", err)
	}

	requisicaoHTTP, err := http.NewRequestWithContext(
		ctx, http.MethodPost, c.urlBase+"/otimizar", bytes.NewReader(corpo))
	if err != nil {
		return Resposta{}, fmt.Errorf("montar requisição para o otimizador: %w", err)
	}
	requisicaoHTTP.Header.Set("Content-Type", "application/json")

	respostaHTTP, err := c.http.Do(requisicaoHTTP)
	if err != nil {
		return Resposta{}, fmt.Errorf("chamar otimizador: %w: %w",
			dominio.ErrOtimizadorIndisponivel, err)
	}
	defer func() {
		_ = respostaHTTP.Body.Close()
	}()

	corpoResposta, err := io.ReadAll(respostaHTTP.Body)
	if err != nil {
		return Resposta{}, fmt.Errorf("ler resposta do otimizador: %w: %w",
			dominio.ErrOtimizadorIndisponivel, err)
	}

	if respostaHTTP.StatusCode >= 500 {
		return Resposta{}, fmt.Errorf("chamar otimizador: %w: status %d: %s",
			dominio.ErrOtimizadorIndisponivel, respostaHTTP.StatusCode, truncar(corpoResposta))
	}
	if respostaHTTP.StatusCode != http.StatusOK {
		return Resposta{}, fmt.Errorf(
			"otimizador recusou o payload montado pela API: status %d: %s",
			respostaHTTP.StatusCode, truncar(corpoResposta))
	}

	var resposta Resposta
	if err := json.Unmarshal(corpoResposta, &resposta); err != nil {
		return Resposta{}, fmt.Errorf("interpretar resposta do otimizador: %w", err)
	}
	resposta.Bruto = json.RawMessage(corpoResposta)
	return resposta, nil
}

// Saude consulta GET /saude do serviço Python. Usado por GET /saude da API.
func (c *Cliente) Saude(ctx context.Context) error {
	requisicaoHTTP, err := http.NewRequestWithContext(
		ctx, http.MethodGet, c.urlBase+"/saude", nil)
	if err != nil {
		return fmt.Errorf("montar requisição de saúde do otimizador: %w", err)
	}

	respostaHTTP, err := c.http.Do(requisicaoHTTP)
	if err != nil {
		return fmt.Errorf("consultar saúde do otimizador: %w: %w",
			dominio.ErrOtimizadorIndisponivel, err)
	}
	defer func() {
		_ = respostaHTTP.Body.Close()
	}()
	_, _ = io.Copy(io.Discard, io.LimitReader(respostaHTTP.Body, limiteCorpoErro))

	if respostaHTTP.StatusCode != http.StatusOK {
		return fmt.Errorf("consultar saúde do otimizador: %w: status %d",
			dominio.ErrOtimizadorIndisponivel, respostaHTTP.StatusCode)
	}
	return nil
}

func truncar(corpo []byte) string {
	if len(corpo) > limiteCorpoErro {
		return string(corpo[:limiteCorpoErro]) + "..."
	}
	return string(corpo)
}
