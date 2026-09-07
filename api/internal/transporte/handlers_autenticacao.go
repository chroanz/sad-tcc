package transporte

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"github.com/tcc/sad-compras/api/internal/servico"
)

type manipuladorAutenticacao struct {
	autenticacao *servico.Autenticacao
}

type corpoRegistro struct {
	Nome  string `json:"nome"`
	Email string `json:"email"`
	Senha string `json:"senha"`
}

type corpoLogin struct {
	Email string `json:"email"`
	Senha string `json:"senha"`
}

func (m *manipuladorAutenticacao) registrar(c *gin.Context) {
	var corpo corpoRegistro
	if err := c.ShouldBindJSON(&corpo); err != nil {
		responderValidacao(c, "corpo inválido: informe nome, email e senha")
		return
	}

	sessao, err := m.autenticacao.Registrar(
		c.Request.Context(), corpo.Nome, corpo.Email, corpo.Senha)
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusCreated, sessao)
}

func (m *manipuladorAutenticacao) entrar(c *gin.Context) {
	var corpo corpoLogin
	if err := c.ShouldBindJSON(&corpo); err != nil {
		responderValidacao(c, "corpo inválido: informe email e senha")
		return
	}

	sessao, err := m.autenticacao.Entrar(c.Request.Context(), corpo.Email, corpo.Senha)
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusOK, sessao)
}
