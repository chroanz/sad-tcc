package transporte

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"github.com/tcc/sad-compras/api/internal/servico"
)

type manipuladorRecomendacao struct {
	recomendacao *servico.Recomendacao
}

// gerar dispara uma nova otimização para a lista.
func (m *manipuladorRecomendacao) gerar(c *gin.Context) {
	listaID, ok := parametroInteiro(c, "id")
	if !ok {
		return
	}

	var pedido servico.PedidoRecomendacao
	if err := c.ShouldBindJSON(&pedido); err != nil {
		responderValidacao(c, "corpo inválido: informe perfil ou peso_conveniencia")
		return
	}

	gerada, err := m.recomendacao.Gerar(
		c.Request.Context(), listaID, usuarioAutenticado(c), pedido)
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusCreated, gerada)
}

// listarHistorico devolve as recomendações já geradas para a lista.
func (m *manipuladorRecomendacao) listarHistorico(c *gin.Context) {
	listaID, ok := parametroInteiro(c, "id")
	if !ok {
		return
	}

	historico, err := m.recomendacao.ListarHistorico(
		c.Request.Context(), listaID, usuarioAutenticado(c))
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusOK, historico)
}

// buscar reabre uma recomendação a partir do payload persistido, sem recalcular.
func (m *manipuladorRecomendacao) buscar(c *gin.Context) {
	recomendacaoID, ok := parametroInteiro(c, "id")
	if !ok {
		return
	}

	gerada, err := m.recomendacao.Buscar(
		c.Request.Context(), recomendacaoID, usuarioAutenticado(c))
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusOK, gerada)
}
