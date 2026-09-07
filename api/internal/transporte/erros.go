// Package transporte expõe a API HTTP com Gin. Handlers são finos: leem a
// requisição, chamam um serviço e escrevem a resposta. Nenhuma regra de negócio
// vive aqui.
package transporte

import (
	"errors"
	"net/http"

	"github.com/gin-gonic/gin"

	"github.com/tcc/sad-compras/api/internal/dominio"
)

// Códigos de erro do contrato REST.
const (
	CodigoValidacao              = "VALIDACAO"
	CodigoNaoAutenticado         = "NAO_AUTENTICADO"
	CodigoNaoAutorizado          = "NAO_AUTORIZADO"
	CodigoNaoEncontrado          = "NAO_ENCONTRADO"
	CodigoConflito               = "CONFLITO"
	CodigoOtimizadorIndisponivel = "OTIMIZADOR_INDISPONIVEL"
	CodigoErroInterno            = "ERRO_INTERNO"
)

// corpoErro é o envelope único de falha: {"erro": {...}}.
type corpoErro struct {
	Erro detalheErro `json:"erro"`
}

type detalheErro struct {
	Codigo   string `json:"codigo"`
	Mensagem string `json:"mensagem"`
	Detalhes any    `json:"detalhes"`
}

// responderErro traduz um erro de domínio no par (status HTTP, código) do
// contrato. É o único lugar do sistema que faz essa tradução — serviços e
// repositórios não conhecem HTTP.
//
// Erros inesperados viram 500 com mensagem genérica: a mensagem interna fica no
// log, não na resposta.
func responderErro(c *gin.Context, err error) {
	var erroValidacao *dominio.ErroValidacao
	switch {
	case errors.As(err, &erroValidacao):
		escrever(c, http.StatusBadRequest, CodigoValidacao, erroValidacao.Mensagem)
	case errors.Is(err, dominio.ErrNaoAutenticado):
		escrever(c, http.StatusUnauthorized, CodigoNaoAutenticado,
			"credenciais inválidas ou sessão expirada")
	case errors.Is(err, dominio.ErrNaoAutorizado):
		escrever(c, http.StatusForbidden, CodigoNaoAutorizado,
			"este recurso pertence a outro usuário")
	case errors.Is(err, dominio.ErrNaoEncontrado):
		escrever(c, http.StatusNotFound, CodigoNaoEncontrado, "recurso não encontrado")
	case errors.Is(err, dominio.ErrConflito):
		escrever(c, http.StatusConflict, CodigoConflito, mensagemDoConflito(err))
	case errors.Is(err, dominio.ErrOtimizadorIndisponivel):
		escrever(c, http.StatusServiceUnavailable, CodigoOtimizadorIndisponivel,
			"serviço de otimização indisponível; tente novamente")
	default:
		_ = c.Error(err)
		escrever(c, http.StatusInternalServerError, CodigoErroInterno,
			"erro interno ao processar a requisição")
	}
}

// mensagemDoConflito extrai a mensagem específica do conflito, quando houver.
func mensagemDoConflito(err error) string {
	var conflito *dominio.ErroConflito
	if errors.As(err, &conflito) {
		return conflito.Mensagem
	}
	return "conflito com registro existente"
}

func escrever(c *gin.Context, status int, codigo, mensagem string) {
	c.AbortWithStatusJSON(status, corpoErro{
		Erro: detalheErro{Codigo: codigo, Mensagem: mensagem},
	})
}

// responderValidacao é o atalho para erro de corpo malformado.
func responderValidacao(c *gin.Context, mensagem string) {
	escrever(c, http.StatusBadRequest, CodigoValidacao, mensagem)
}
