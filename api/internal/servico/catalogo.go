package servico

import (
	"context"
	"strings"
	"time"

	"github.com/tcc/sad-compras/api/internal/dominio"
	"github.com/tcc/sad-compras/api/internal/repositorio"
)

// Catalogo expõe produtos, marcas, mercados e o registro de preços.
type Catalogo struct {
	repositorio *repositorio.Repositorio
}

// NovoCatalogo monta o serviço de catálogo.
func NovoCatalogo(repo *repositorio.Repositorio) *Catalogo {
	return &Catalogo{repositorio: repo}
}

// ListarProdutos devolve o catálogo, com filtro opcional por nome.
func (c *Catalogo) ListarProdutos(
	ctx context.Context, busca string,
) ([]dominio.Produto, error) {
	return c.repositorio.ListarProdutos(ctx, strings.TrimSpace(busca))
}

// CriarProduto cadastra um produto genérico.
func (c *Catalogo) CriarProduto(
	ctx context.Context, nome, categoria string,
) (dominio.Produto, error) {
	nome = strings.TrimSpace(nome)
	categoria = strings.TrimSpace(categoria)
	if nome == "" {
		return dominio.Produto{}, dominio.NovoErroValidacao("nome do produto é obrigatório")
	}
	if categoria == "" {
		return dominio.Produto{}, dominio.NovoErroValidacao("categoria é obrigatória")
	}
	return c.repositorio.CriarProduto(ctx, nome, categoria)
}

// ListarMarcasDoProduto devolve as marcas de um produto.
func (c *Catalogo) ListarMarcasDoProduto(
	ctx context.Context, produtoID int64,
) ([]dominio.Marca, error) {
	return c.repositorio.ListarMarcasDoProduto(ctx, produtoID)
}

// CriarMarca cadastra uma variante comercial de um produto.
func (c *Catalogo) CriarMarca(
	ctx context.Context, produtoID int64, nome string,
) (dominio.Marca, error) {
	nome = strings.TrimSpace(nome)
	if produtoID <= 0 {
		return dominio.Marca{}, dominio.NovoErroValidacao("produto_id é obrigatório")
	}
	if nome == "" {
		return dominio.Marca{}, dominio.NovoErroValidacao("nome da marca é obrigatório")
	}
	return c.repositorio.CriarMarca(ctx, produtoID, nome)
}

// ListarMercados devolve os supermercados cadastrados.
func (c *Catalogo) ListarMercados(ctx context.Context) ([]dominio.Mercado, error) {
	return c.repositorio.ListarMercados(ctx)
}

// CriarMercado cadastra um supermercado, validando as coordenadas antes de
// deixar o CHECK do banco reprovar com mensagem menos clara.
func (c *Catalogo) CriarMercado(
	ctx context.Context, nome string, latitude, longitude float64, endereco string,
) (dominio.Mercado, error) {
	nome = strings.TrimSpace(nome)
	endereco = strings.TrimSpace(endereco)
	if nome == "" {
		return dominio.Mercado{}, dominio.NovoErroValidacao("nome do mercado é obrigatório")
	}
	if endereco == "" {
		return dominio.Mercado{}, dominio.NovoErroValidacao("endereço é obrigatório")
	}
	if latitude < -90 || latitude > 90 {
		return dominio.Mercado{}, dominio.NovoErroValidacao("latitude fora da faixa [-90, 90]")
	}
	if longitude < -180 || longitude > 180 {
		return dominio.Mercado{}, dominio.NovoErroValidacao("longitude fora da faixa [-180, 180]")
	}
	return c.repositorio.CriarMercado(ctx, nome, latitude, longitude, endereco)
}

// ListarPrecos devolve preços vigentes ou o histórico completo.
func (c *Catalogo) ListarPrecos(
	ctx context.Context, mercadoID, marcaID *int64, vigentes bool,
) ([]dominio.Preco, error) {
	return c.repositorio.ListarPrecos(ctx, mercadoID, marcaID, vigentes)
}

// RegistrarPreco grava um novo snapshot de preço.
//
// Não existe atualização de preço: cada coleta é um INSERT. É essa decisão que
// preserva a série histórica usada na fundamentação teórica do TCC.
func (c *Catalogo) RegistrarPreco(
	ctx context.Context,
	marcaID, mercadoID, precoCentavos int64,
	unidade string,
	quantidadeDisponivel float64,
	coletadoEm *time.Time,
) (dominio.Preco, error) {
	if marcaID <= 0 || mercadoID <= 0 {
		return dominio.Preco{}, dominio.NovoErroValidacao(
			"marca_id e mercado_id são obrigatórios")
	}
	if precoCentavos <= 0 {
		return dominio.Preco{}, dominio.NovoErroValidacao("preço deve ser maior que zero")
	}
	if quantidadeDisponivel < 0 {
		return dominio.Preco{}, dominio.NovoErroValidacao(
			"quantidade disponível não pode ser negativa")
	}
	if err := dominio.ValidarUnidade(unidade); err != nil {
		return dominio.Preco{}, err
	}
	return c.repositorio.RegistrarPreco(
		ctx, marcaID, mercadoID, precoCentavos, unidade, quantidadeDisponivel, coletadoEm)
}
