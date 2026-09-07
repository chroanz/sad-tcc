package repositorio

import (
	"context"
	"fmt"
	"time"

	"github.com/tcc/sad-compras/api/internal/dominio"
)

// ListarProdutos devolve o catálogo de produtos, opcionalmente filtrado por
// trecho do nome (busca vazia devolve tudo).
func (r *Repositorio) ListarProdutos(
	ctx context.Context, busca string,
) ([]dominio.Produto, error) {
	const consulta = `
		SELECT id, nome, categoria, criado_em
		  FROM produtos
		 WHERE ($1 = '' OR nome ILIKE '%' || $1 || '%')
		 ORDER BY nome`

	linhas, err := r.pool.Query(ctx, consulta, busca)
	if err != nil {
		return nil, fmt.Errorf("listar produtos: %w", err)
	}
	defer linhas.Close()

	produtos := make([]dominio.Produto, 0)
	for linhas.Next() {
		var produto dominio.Produto
		if err := linhas.Scan(
			&produto.ID, &produto.Nome, &produto.Categoria, &produto.CriadoEm,
		); err != nil {
			return nil, fmt.Errorf("ler produto: %w", err)
		}
		produtos = append(produtos, produto)
	}
	return produtos, linhas.Err()
}

// CriarProduto insere um produto genérico da cesta.
func (r *Repositorio) CriarProduto(
	ctx context.Context, nome, categoria string,
) (dominio.Produto, error) {
	const consulta = `
		INSERT INTO produtos (nome, categoria)
		VALUES ($1, $2)
		RETURNING id, nome, categoria, criado_em`

	var produto dominio.Produto
	err := r.pool.QueryRow(ctx, consulta, nome, categoria).Scan(
		&produto.ID, &produto.Nome, &produto.Categoria, &produto.CriadoEm,
	)
	if err != nil {
		return dominio.Produto{}, fmt.Errorf(
			"criar produto: %w", traduzirErro(err, "produto já cadastrado"))
	}
	return produto, nil
}

// ListarMarcasDoProduto devolve as variantes comerciais de um produto.
func (r *Repositorio) ListarMarcasDoProduto(
	ctx context.Context, produtoID int64,
) ([]dominio.Marca, error) {
	const consulta = `
		SELECT id, produto_id, nome, criado_em
		  FROM marcas
		 WHERE produto_id = $1
		 ORDER BY nome`

	linhas, err := r.pool.Query(ctx, consulta, produtoID)
	if err != nil {
		return nil, fmt.Errorf("listar marcas: %w", err)
	}
	defer linhas.Close()

	marcas := make([]dominio.Marca, 0)
	for linhas.Next() {
		var marca dominio.Marca
		if err := linhas.Scan(
			&marca.ID, &marca.ProdutoID, &marca.Nome, &marca.CriadoEm,
		); err != nil {
			return nil, fmt.Errorf("ler marca: %w", err)
		}
		marcas = append(marcas, marca)
	}
	return marcas, linhas.Err()
}

// CriarMarca insere uma marca de um produto. O par (produto_id, nome) é único.
func (r *Repositorio) CriarMarca(
	ctx context.Context, produtoID int64, nome string,
) (dominio.Marca, error) {
	const consulta = `
		INSERT INTO marcas (produto_id, nome)
		VALUES ($1, $2)
		RETURNING id, produto_id, nome, criado_em`

	var marca dominio.Marca
	err := r.pool.QueryRow(ctx, consulta, produtoID, nome).Scan(
		&marca.ID, &marca.ProdutoID, &marca.Nome, &marca.CriadoEm,
	)
	if err != nil {
		return dominio.Marca{}, fmt.Errorf(
			"criar marca: %w", traduzirErro(err, "marca já cadastrada para este produto"))
	}
	return marca, nil
}

// ListarMercados devolve todos os supermercados do recorte, com coordenadas.
func (r *Repositorio) ListarMercados(ctx context.Context) ([]dominio.Mercado, error) {
	const consulta = `
		SELECT id, nome, latitude::float8, longitude::float8, endereco, criado_em
		  FROM mercados
		 ORDER BY nome`

	linhas, err := r.pool.Query(ctx, consulta)
	if err != nil {
		return nil, fmt.Errorf("listar mercados: %w", err)
	}
	defer linhas.Close()

	mercados := make([]dominio.Mercado, 0)
	for linhas.Next() {
		var mercado dominio.Mercado
		if err := linhas.Scan(
			&mercado.ID, &mercado.Nome, &mercado.Latitude,
			&mercado.Longitude, &mercado.Endereco, &mercado.CriadoEm,
		); err != nil {
			return nil, fmt.Errorf("ler mercado: %w", err)
		}
		mercados = append(mercados, mercado)
	}
	return mercados, linhas.Err()
}

// CriarMercado insere um supermercado.
func (r *Repositorio) CriarMercado(
	ctx context.Context, nome string, latitude, longitude float64, endereco string,
) (dominio.Mercado, error) {
	const consulta = `
		INSERT INTO mercados (nome, latitude, longitude, endereco)
		VALUES ($1, $2, $3, $4)
		RETURNING id, nome, latitude::float8, longitude::float8, endereco, criado_em`

	var mercado dominio.Mercado
	err := r.pool.QueryRow(ctx, consulta, nome, latitude, longitude, endereco).Scan(
		&mercado.ID, &mercado.Nome, &mercado.Latitude,
		&mercado.Longitude, &mercado.Endereco, &mercado.CriadoEm,
	)
	if err != nil {
		return dominio.Mercado{}, fmt.Errorf("criar mercado: %w", traduzirErro(err, ""))
	}
	return mercado, nil
}

// RegistrarPreco insere um novo snapshot de preço. Nunca há UPDATE: a série
// histórica de `precos` é append-only por decisão de modelagem.
func (r *Repositorio) RegistrarPreco(
	ctx context.Context,
	marcaID, mercadoID int64,
	precoCentavos int64,
	unidade string,
	quantidadeDisponivel float64,
	coletadoEm *time.Time,
) (dominio.Preco, error) {
	const consulta = `
		INSERT INTO precos (marca_id, mercado_id, preco, unidade, quantidade_disponivel, coletado_em)
		VALUES ($1, $2, $3::numeric, $4, $5, COALESCE($6, now()))
		RETURNING id, marca_id, mercado_id, preco::text, unidade,
		          quantidade_disponivel::float8, coletado_em`

	var preco dominio.Preco
	var precoTexto string
	err := r.pool.QueryRow(
		ctx, consulta, marcaID, mercadoID,
		dominio.ConverterCentavosParaReais(precoCentavos),
		unidade, quantidadeDisponivel, coletadoEm,
	).Scan(
		&preco.ID, &preco.MarcaID, &preco.MercadoID, &precoTexto,
		&preco.Unidade, &preco.QuantidadeDisponivel, &preco.ColetadoEm,
	)
	if err != nil {
		return dominio.Preco{}, fmt.Errorf("registrar preço: %w", traduzirErro(err, ""))
	}

	preco.PrecoCentavos, err = dominio.ConverterReaisParaCentavos(precoTexto)
	if err != nil {
		return dominio.Preco{}, fmt.Errorf("converter preço registrado: %w", err)
	}
	return preco, nil
}

// ListarPrecos devolve snapshots de preço. Com `vigentes` verdadeiro a leitura
// vem da view precos_vigentes (um registro por par marca/mercado); caso
// contrário devolve o histórico completo, mais recente primeiro.
func (r *Repositorio) ListarPrecos(
	ctx context.Context, mercadoID, marcaID *int64, vigentes bool,
) ([]dominio.Preco, error) {
	const consultaVigentes = `
		SELECT pv.preco_id, pv.marca_id, pv.mercado_id, pv.preco::text, pv.unidade,
		       pv.quantidade_disponivel::float8, pv.coletado_em, ma.nome, me.nome
		  FROM precos_vigentes pv
		  JOIN marcas ma ON ma.id = pv.marca_id
		  JOIN mercados me ON me.id = pv.mercado_id
		 WHERE ($1::bigint IS NULL OR pv.mercado_id = $1)
		   AND ($2::bigint IS NULL OR pv.marca_id = $2)
		 ORDER BY me.nome, ma.nome`

	const consultaHistorico = `
		SELECT p.id, p.marca_id, p.mercado_id, p.preco::text, p.unidade,
		       p.quantidade_disponivel::float8, p.coletado_em, ma.nome, me.nome
		  FROM precos p
		  JOIN marcas ma ON ma.id = p.marca_id
		  JOIN mercados me ON me.id = p.mercado_id
		 WHERE ($1::bigint IS NULL OR p.mercado_id = $1)
		   AND ($2::bigint IS NULL OR p.marca_id = $2)
		 ORDER BY p.coletado_em DESC, p.id DESC`

	consulta := consultaHistorico
	if vigentes {
		consulta = consultaVigentes
	}

	linhas, err := r.pool.Query(ctx, consulta, mercadoID, marcaID)
	if err != nil {
		return nil, fmt.Errorf("listar preços: %w", err)
	}
	defer linhas.Close()

	precos := make([]dominio.Preco, 0)
	for linhas.Next() {
		var preco dominio.Preco
		var precoTexto string
		if err := linhas.Scan(
			&preco.ID, &preco.MarcaID, &preco.MercadoID, &precoTexto, &preco.Unidade,
			&preco.QuantidadeDisponivel, &preco.ColetadoEm, &preco.MarcaNome, &preco.MercadoNome,
		); err != nil {
			return nil, fmt.Errorf("ler preço: %w", err)
		}
		if preco.PrecoCentavos, err = dominio.ConverterReaisParaCentavos(precoTexto); err != nil {
			return nil, fmt.Errorf("converter preço lido: %w", err)
		}
		precos = append(precos, preco)
	}
	return precos, linhas.Err()
}

// OfertaVigente é uma linha de precos_vigentes já resolvida com o produto a que
// a marca pertence. Serve de matéria-prima para os candidatos da otimização.
type OfertaVigente struct {
	ProdutoID             int64
	MarcaID               int64
	MarcaNome             string
	MercadoID             int64
	PrecoUnitarioCentavos int64
	QuantidadeDisponivel  float64
	Unidade               string
}

// BuscarOfertasVigentes devolve, para um conjunto de produtos, todas as ofertas
// vigentes em todos os mercados.
//
// A leitura vem da view precos_vigentes, e não da tabela precos: só o snapshot
// mais recente de cada par (marca, mercado) pode alimentar uma recomendação.
func (r *Repositorio) BuscarOfertasVigentes(
	ctx context.Context, produtoIDs []int64,
) ([]OfertaVigente, error) {
	if len(produtoIDs) == 0 {
		return nil, nil
	}

	const consulta = `
		SELECT ma.produto_id, pv.marca_id, ma.nome, pv.mercado_id,
		       pv.preco::text, pv.quantidade_disponivel::float8, pv.unidade
		  FROM precos_vigentes pv
		  JOIN marcas ma ON ma.id = pv.marca_id
		 WHERE ma.produto_id = ANY($1::bigint[])
		 ORDER BY ma.produto_id, pv.mercado_id, pv.marca_id`

	linhas, err := r.pool.Query(ctx, consulta, produtoIDs)
	if err != nil {
		return nil, fmt.Errorf("buscar ofertas vigentes: %w", err)
	}
	defer linhas.Close()

	ofertas := make([]OfertaVigente, 0)
	for linhas.Next() {
		var oferta OfertaVigente
		var precoTexto string
		if err := linhas.Scan(
			&oferta.ProdutoID, &oferta.MarcaID, &oferta.MarcaNome, &oferta.MercadoID,
			&precoTexto, &oferta.QuantidadeDisponivel, &oferta.Unidade,
		); err != nil {
			return nil, fmt.Errorf("ler oferta vigente: %w", err)
		}
		if oferta.PrecoUnitarioCentavos, err = dominio.ConverterReaisParaCentavos(
			precoTexto,
		); err != nil {
			return nil, fmt.Errorf("converter preço da oferta: %w", err)
		}
		ofertas = append(ofertas, oferta)
	}
	return ofertas, linhas.Err()
}
