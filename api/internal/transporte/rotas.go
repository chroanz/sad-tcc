package transporte

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"github.com/tcc/sad-compras/api/internal/servico"
)

// Dependencias reúne o que a camada HTTP precisa para montar as rotas.
type Dependencias struct {
	Autenticacao *servico.Autenticacao
	Catalogo     *servico.Catalogo
	Lista        *servico.Lista
	Recomendacao *servico.Recomendacao
	Saude        *servico.Saude
}

// MontarRoteador registra todas as rotas do contrato REST.
//
// A separação entre o grupo público e o protegido é explícita: tudo que fica
// abaixo de `protegido` passa obrigatoriamente pelo middleware de autenticação.
func MontarRoteador(deps Dependencias) *gin.Engine {
	roteador := gin.New()
	roteador.Use(gin.Logger(), gin.Recovery(), liberarCORS())

	autenticacao := &manipuladorAutenticacao{autenticacao: deps.Autenticacao}
	catalogo := &manipuladorCatalogo{catalogo: deps.Catalogo}
	lista := &manipuladorLista{lista: deps.Lista}
	recomendacao := &manipuladorRecomendacao{recomendacao: deps.Recomendacao}

	roteador.GET("/saude", func(c *gin.Context) {
		relatorio := deps.Saude.Verificar(c.Request.Context())
		status := http.StatusOK
		if relatorio.Status != "ok" {
			status = http.StatusServiceUnavailable
		}
		c.JSON(status, relatorio)
	})

	v1 := roteador.Group("/api/v1")
	{
		v1.POST("/auth/registrar", autenticacao.registrar)
		v1.POST("/auth/entrar", autenticacao.entrar)

		protegido := v1.Group("")
		protegido.Use(exigirAutenticacao(deps.Autenticacao))
		{
			protegido.GET("/produtos", catalogo.listarProdutos)
			protegido.POST("/produtos", catalogo.criarProduto)
			protegido.GET("/produtos/:id/marcas", catalogo.listarMarcas)
			protegido.POST("/marcas", catalogo.criarMarca)
			protegido.GET("/mercados", catalogo.listarMercados)
			protegido.POST("/mercados", catalogo.criarMercado)
			protegido.GET("/precos", catalogo.listarPrecos)
			protegido.POST("/precos", catalogo.registrarPreco)

			protegido.GET("/listas", lista.listar)
			protegido.POST("/listas", lista.criar)
			protegido.GET("/listas/:id", lista.buscar)
			protegido.PUT("/listas/:id", lista.renomear)
			protegido.DELETE("/listas/:id", lista.remover)
			protegido.POST("/listas/:id/itens", lista.adicionarItem)
			protegido.PUT("/listas/:id/itens/:item_id", lista.atualizarItem)
			protegido.DELETE("/listas/:id/itens/:item_id", lista.removerItem)

			protegido.POST("/listas/:id/recomendacoes", recomendacao.gerar)
			protegido.GET("/listas/:id/recomendacoes", recomendacao.listarHistorico)
			protegido.GET("/recomendacoes/:id", recomendacao.buscar)
		}
	}

	return roteador
}
