package transporte

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"

	"github.com/tcc/sad-compras/api/internal/dominio"
	"github.com/tcc/sad-compras/api/internal/servico"
)

type manipuladorCatalogo struct {
	catalogo *servico.Catalogo
}

type corpoProduto struct {
	Nome      string `json:"nome"`
	Categoria string `json:"categoria"`
}

type corpoMarca struct {
	ProdutoID int64  `json:"produto_id"`
	Nome      string `json:"nome"`
}

type corpoMercado struct {
	Nome      string  `json:"nome"`
	Latitude  float64 `json:"latitude"`
	Longitude float64 `json:"longitude"`
	Endereco  string  `json:"endereco"`
}

// corpoPreco recebe o preço em reais decimais e o converte para centavos sem
// passar por float64, como exige o contrato.
type corpoPreco struct {
	MarcaID              int64      `json:"marca_id"`
	MercadoID            int64      `json:"mercado_id"`
	Preco                string     `json:"preco"`
	Unidade              string     `json:"unidade"`
	QuantidadeDisponivel float64    `json:"quantidade_disponivel"`
	ColetadoEm           *time.Time `json:"coletado_em"`
}

func (m *manipuladorCatalogo) listarProdutos(c *gin.Context) {
	produtos, err := m.catalogo.ListarProdutos(c.Request.Context(), c.Query("busca"))
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusOK, produtos)
}

func (m *manipuladorCatalogo) criarProduto(c *gin.Context) {
	var corpo corpoProduto
	if err := c.ShouldBindJSON(&corpo); err != nil {
		responderValidacao(c, "corpo inválido: informe nome e categoria")
		return
	}

	produto, err := m.catalogo.CriarProduto(c.Request.Context(), corpo.Nome, corpo.Categoria)
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusCreated, produto)
}

func (m *manipuladorCatalogo) listarMarcas(c *gin.Context) {
	produtoID, ok := parametroInteiro(c, "id")
	if !ok {
		return
	}

	marcas, err := m.catalogo.ListarMarcasDoProduto(c.Request.Context(), produtoID)
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusOK, marcas)
}

func (m *manipuladorCatalogo) criarMarca(c *gin.Context) {
	var corpo corpoMarca
	if err := c.ShouldBindJSON(&corpo); err != nil {
		responderValidacao(c, "corpo inválido: informe produto_id e nome")
		return
	}

	marca, err := m.catalogo.CriarMarca(c.Request.Context(), corpo.ProdutoID, corpo.Nome)
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusCreated, marca)
}

func (m *manipuladorCatalogo) listarMercados(c *gin.Context) {
	mercados, err := m.catalogo.ListarMercados(c.Request.Context())
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusOK, mercados)
}

func (m *manipuladorCatalogo) criarMercado(c *gin.Context) {
	var corpo corpoMercado
	if err := c.ShouldBindJSON(&corpo); err != nil {
		responderValidacao(c, "corpo inválido: informe nome, latitude, longitude e endereço")
		return
	}

	mercado, err := m.catalogo.CriarMercado(
		c.Request.Context(), corpo.Nome, corpo.Latitude, corpo.Longitude, corpo.Endereco)
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusCreated, mercado)
}

func (m *manipuladorCatalogo) listarPrecos(c *gin.Context) {
	mercadoID, ok := consultaInteiraOpcional(c, "mercado_id")
	if !ok {
		return
	}
	marcaID, ok := consultaInteiraOpcional(c, "marca_id")
	if !ok {
		return
	}

	precos, err := m.catalogo.ListarPrecos(
		c.Request.Context(), mercadoID, marcaID, c.Query("vigentes") == "true")
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusOK, precos)
}

// registrarPreco insere um novo snapshot. Não existe rota de atualização de
// preço: a tabela é append-only para preservar a série histórica.
func (m *manipuladorCatalogo) registrarPreco(c *gin.Context) {
	var corpo corpoPreco
	if err := c.ShouldBindJSON(&corpo); err != nil {
		responderValidacao(c, "corpo inválido: informe marca_id, mercado_id, preco e unidade")
		return
	}

	centavos, err := dominio.ConverterReaisParaCentavos(corpo.Preco)
	if err != nil {
		responderErro(c, err)
		return
	}

	preco, err := m.catalogo.RegistrarPreco(
		c.Request.Context(), corpo.MarcaID, corpo.MercadoID, centavos,
		corpo.Unidade, corpo.QuantidadeDisponivel, corpo.ColetadoEm)
	if err != nil {
		responderErro(c, err)
		return
	}
	c.JSON(http.StatusCreated, preco)
}
