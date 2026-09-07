package transporte

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"github.com/tcc/sad-compras/api/internal/servico"
)

type manipuladorLista struct {
	lista *servico.Lista
}

type corpoLista struct {
	Nome string `json:"nome"`
}

// corpoItem representa um item da lista. MarcaID é ponteiro porque nulo tem
// significado próprio: qualquer marca do produto serve.
type corpoItem struct {
	ProdutoID  int64   `json:"produto_id"`
	MarcaID    *int64  `json:"marca_id"`
	Quantidade float64 `json:"quantidade"`
	Unidade    string  `json:"unidade"`
}

func (m *manipuladorLista) listar(c *gin.Context) {
	listas, err := m.lista.Listar(c.Request.Context(), usuarioAutenticado(c))
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusOK, listas)
}

func (m *manipuladorLista) criar(c *gin.Context) {
	var corpo corpoLista
	if err := c.ShouldBindJSON(&corpo); err != nil {
		responderValidacao(c, "corpo inválido: informe o nome da lista")
		return
	}

	lista, err := m.lista.Criar(c.Request.Context(), usuarioAutenticado(c), corpo.Nome)
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusCreated, lista)
}

func (m *manipuladorLista) buscar(c *gin.Context) {
	listaID, ok := parametroInteiro(c, "id")
	if !ok {
		return
	}

	lista, err := m.lista.Buscar(c.Request.Context(), listaID, usuarioAutenticado(c))
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusOK, lista)
}

func (m *manipuladorLista) renomear(c *gin.Context) {
	listaID, ok := parametroInteiro(c, "id")
	if !ok {
		return
	}

	var corpo corpoLista
	if err := c.ShouldBindJSON(&corpo); err != nil {
		responderValidacao(c, "corpo inválido: informe o nome da lista")
		return
	}

	lista, err := m.lista.Renomear(
		c.Request.Context(), listaID, usuarioAutenticado(c), corpo.Nome)
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusOK, lista)
}

func (m *manipuladorLista) remover(c *gin.Context) {
	listaID, ok := parametroInteiro(c, "id")
	if !ok {
		return
	}

	if err := m.lista.Remover(c.Request.Context(), listaID, usuarioAutenticado(c)); err != nil {
		responderErro(c, err)
		return
	}
	c.Status(http.StatusNoContent)
}

func (m *manipuladorLista) adicionarItem(c *gin.Context) {
	listaID, ok := parametroInteiro(c, "id")
	if !ok {
		return
	}

	var corpo corpoItem
	if err := c.ShouldBindJSON(&corpo); err != nil {
		responderValidacao(c, "corpo inválido: informe produto_id, quantidade e unidade")
		return
	}

	item, err := m.lista.AdicionarItem(
		c.Request.Context(), listaID, usuarioAutenticado(c), corpo.ProdutoID,
		corpo.MarcaID, corpo.Quantidade, corpo.Unidade)
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusCreated, item)
}

func (m *manipuladorLista) atualizarItem(c *gin.Context) {
	listaID, ok := parametroInteiro(c, "id")
	if !ok {
		return
	}
	itemID, ok := parametroInteiro(c, "item_id")
	if !ok {
		return
	}

	var corpo corpoItem
	if err := c.ShouldBindJSON(&corpo); err != nil {
		responderValidacao(c, "corpo inválido: informe produto_id, quantidade e unidade")
		return
	}

	item, err := m.lista.AtualizarItem(
		c.Request.Context(), listaID, usuarioAutenticado(c), itemID, corpo.ProdutoID,
		corpo.MarcaID, corpo.Quantidade, corpo.Unidade)
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusOK, item)
}

func (m *manipuladorLista) removerItem(c *gin.Context) {
	listaID, ok := parametroInteiro(c, "id")
	if !ok {
		return
	}
	itemID, ok := parametroInteiro(c, "item_id")
	if !ok {
		return
	}

	err := m.lista.RemoverItem(c.Request.Context(), listaID, usuarioAutenticado(c), itemID)
	if err != nil {
		responderErro(c, err)
		return
	}
	c.Status(http.StatusNoContent)
}
