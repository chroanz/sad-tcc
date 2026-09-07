package transporte

import (
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"

	"github.com/tcc/sad-compras/api/internal/dominio"
	"github.com/tcc/sad-compras/api/internal/servico"
)

// chaveUsuarioID é onde o middleware guarda o id do usuário autenticado no
// contexto da requisição.
const chaveUsuarioID = "usuario_id"

// exigirAutenticacao valida o cabeçalho Authorization e injeta o id do usuário
// no contexto. Sem isso, nenhum handler protegido chega a rodar.
func exigirAutenticacao(autenticacao *servico.Autenticacao) gin.HandlerFunc {
	return func(c *gin.Context) {
		cabecalho := c.GetHeader("Authorization")
		partes := strings.SplitN(cabecalho, " ", 2)
		if len(partes) != 2 || !strings.EqualFold(partes[0], "Bearer") {
			responderErro(c, dominio.ErrNaoAutenticado)
			return
		}

		usuarioID, err := autenticacao.ValidarToken(strings.TrimSpace(partes[1]))
		if err != nil {
			responderErro(c, dominio.ErrNaoAutenticado)
			return
		}

		c.Set(chaveUsuarioID, usuarioID)
		c.Next()
	}
}

// usuarioAutenticado lê o id colocado pelo middleware.
func usuarioAutenticado(c *gin.Context) int64 {
	valor, existe := c.Get(chaveUsuarioID)
	if !existe {
		return 0
	}
	usuarioID, _ := valor.(int64)
	return usuarioID
}

// liberarCORS permite que o PWA, servido em outra porta durante o
// desenvolvimento, converse com a API.
func liberarCORS() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization")
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	}
}

// parametroInteiro lê um parâmetro de rota numérico, respondendo 400 quando ele
// não é um inteiro válido.
func parametroInteiro(c *gin.Context, nome string) (int64, bool) {
	valor, err := strconv.ParseInt(c.Param(nome), 10, 64)
	if err != nil || valor <= 0 {
		responderValidacao(c, "parâmetro "+nome+" inválido")
		return 0, false
	}
	return valor, true
}

// consultaInteiraOpcional lê um parâmetro de query numérico opcional.
func consultaInteiraOpcional(c *gin.Context, nome string) (*int64, bool) {
	bruto := c.Query(nome)
	if bruto == "" {
		return nil, true
	}
	valor, err := strconv.ParseInt(bruto, 10, 64)
	if err != nil {
		responderValidacao(c, "parâmetro de consulta "+nome+" inválido")
		return nil, false
	}
	return &valor, true
}
