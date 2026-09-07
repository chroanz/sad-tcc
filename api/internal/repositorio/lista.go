package repositorio

import (
	"context"
	"fmt"

	"github.com/tcc/sad-compras/api/internal/dominio"
)

// ListarListasDoUsuario devolve as listas do usuário com a contagem de itens.
func (r *Repositorio) ListarListasDoUsuario(
	ctx context.Context, usuarioID int64,
) ([]dominio.Lista, error) {
	const consulta = `
		SELECT l.id, l.usuario_id, l.nome, l.criado_em, count(i.id)
		  FROM listas_compra l
		  LEFT JOIN itens_lista i ON i.lista_id = l.id
		 WHERE l.usuario_id = $1
		 GROUP BY l.id
		 ORDER BY l.criado_em DESC`

	linhas, err := r.pool.Query(ctx, consulta, usuarioID)
	if err != nil {
		return nil, fmt.Errorf("listar listas: %w", err)
	}
	defer linhas.Close()

	listas := make([]dominio.Lista, 0)
	for linhas.Next() {
		var lista dominio.Lista
		if err := linhas.Scan(
			&lista.ID, &lista.UsuarioID, &lista.Nome, &lista.CriadoEm, &lista.QuantidadeItens,
		); err != nil {
			return nil, fmt.Errorf("ler lista: %w", err)
		}
		listas = append(listas, lista)
	}
	return listas, linhas.Err()
}

// CriarLista insere uma lista vazia para o usuário.
func (r *Repositorio) CriarLista(
	ctx context.Context, usuarioID int64, nome string,
) (dominio.Lista, error) {
	const consulta = `
		INSERT INTO listas_compra (usuario_id, nome)
		VALUES ($1, $2)
		RETURNING id, usuario_id, nome, criado_em`

	var lista dominio.Lista
	err := r.pool.QueryRow(ctx, consulta, usuarioID, nome).Scan(
		&lista.ID, &lista.UsuarioID, &lista.Nome, &lista.CriadoEm,
	)
	if err != nil {
		return dominio.Lista{}, fmt.Errorf("criar lista: %w", traduzirErro(err, ""))
	}
	return lista, nil
}

// BuscarLista devolve a lista sem os itens. O UsuarioID é o que permite ao
// serviço conferir a posse antes de qualquer operação.
func (r *Repositorio) BuscarLista(ctx context.Context, listaID int64) (dominio.Lista, error) {
	const consulta = `
		SELECT id, usuario_id, nome, criado_em
		  FROM listas_compra
		 WHERE id = $1`

	var lista dominio.Lista
	err := r.pool.QueryRow(ctx, consulta, listaID).Scan(
		&lista.ID, &lista.UsuarioID, &lista.Nome, &lista.CriadoEm,
	)
	if err != nil {
		return dominio.Lista{}, fmt.Errorf("buscar lista: %w", traduzirErro(err, ""))
	}
	return lista, nil
}

// AtualizarLista renomeia a lista.
func (r *Repositorio) AtualizarLista(
	ctx context.Context, listaID int64, nome string,
) (dominio.Lista, error) {
	const consulta = `
		UPDATE listas_compra
		   SET nome = $2
		 WHERE id = $1
		RETURNING id, usuario_id, nome, criado_em`

	var lista dominio.Lista
	err := r.pool.QueryRow(ctx, consulta, listaID, nome).Scan(
		&lista.ID, &lista.UsuarioID, &lista.Nome, &lista.CriadoEm,
	)
	if err != nil {
		return dominio.Lista{}, fmt.Errorf("atualizar lista: %w", traduzirErro(err, ""))
	}
	return lista, nil
}

// RemoverLista apaga a lista; itens e recomendações caem em cascata.
func (r *Repositorio) RemoverLista(ctx context.Context, listaID int64) error {
	etiqueta, err := r.pool.Exec(ctx, `DELETE FROM listas_compra WHERE id = $1`, listaID)
	if err != nil {
		return fmt.Errorf("remover lista: %w", err)
	}
	if etiqueta.RowsAffected() == 0 {
		return dominio.ErrNaoEncontrado
	}
	return nil
}

// ListarItens devolve os itens da lista com produto e marca já resolvidos.
func (r *Repositorio) ListarItens(
	ctx context.Context, listaID int64,
) ([]dominio.ItemLista, error) {
	const consulta = `
		SELECT i.id, i.lista_id, i.produto_id, p.nome, i.marca_id, ma.nome,
		       i.quantidade::float8, i.unidade
		  FROM itens_lista i
		  JOIN produtos p ON p.id = i.produto_id
		  LEFT JOIN marcas ma ON ma.id = i.marca_id
		 WHERE i.lista_id = $1
		 ORDER BY i.id`

	linhas, err := r.pool.Query(ctx, consulta, listaID)
	if err != nil {
		return nil, fmt.Errorf("listar itens da lista: %w", err)
	}
	defer linhas.Close()

	itens := make([]dominio.ItemLista, 0)
	for linhas.Next() {
		var item dominio.ItemLista
		if err := linhas.Scan(
			&item.ID, &item.ListaID, &item.ProdutoID, &item.ProdutoNome,
			&item.MarcaID, &item.MarcaNome, &item.Quantidade, &item.Unidade,
		); err != nil {
			return nil, fmt.Errorf("ler item da lista: %w", err)
		}
		itens = append(itens, item)
	}
	return itens, linhas.Err()
}

// AdicionarItem insere um item na lista. MarcaID nulo significa indiferença de
// marca: qualquer marca do produto poderá ser usada pelo otimizador.
func (r *Repositorio) AdicionarItem(
	ctx context.Context,
	listaID, produtoID int64,
	marcaID *int64,
	quantidade float64,
	unidade string,
) (dominio.ItemLista, error) {
	const consulta = `
		INSERT INTO itens_lista (lista_id, produto_id, marca_id, quantidade, unidade)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id`

	var itemID int64
	err := r.pool.QueryRow(
		ctx, consulta, listaID, produtoID, marcaID, quantidade, unidade,
	).Scan(&itemID)
	if err != nil {
		return dominio.ItemLista{}, fmt.Errorf("adicionar item: %w", traduzirErro(err, ""))
	}
	return r.BuscarItem(ctx, itemID)
}

// AtualizarItem altera marca, quantidade e unidade de um item já existente.
func (r *Repositorio) AtualizarItem(
	ctx context.Context,
	itemID, produtoID int64,
	marcaID *int64,
	quantidade float64,
	unidade string,
) (dominio.ItemLista, error) {
	const consulta = `
		UPDATE itens_lista
		   SET produto_id = $2, marca_id = $3, quantidade = $4, unidade = $5
		 WHERE id = $1
		RETURNING id`

	var atualizado int64
	err := r.pool.QueryRow(
		ctx, consulta, itemID, produtoID, marcaID, quantidade, unidade,
	).Scan(&atualizado)
	if err != nil {
		return dominio.ItemLista{}, fmt.Errorf("atualizar item: %w", traduzirErro(err, ""))
	}
	return r.BuscarItem(ctx, atualizado)
}

// BuscarItem devolve um item com produto e marca resolvidos.
func (r *Repositorio) BuscarItem(ctx context.Context, itemID int64) (dominio.ItemLista, error) {
	const consulta = `
		SELECT i.id, i.lista_id, i.produto_id, p.nome, i.marca_id, ma.nome,
		       i.quantidade::float8, i.unidade
		  FROM itens_lista i
		  JOIN produtos p ON p.id = i.produto_id
		  LEFT JOIN marcas ma ON ma.id = i.marca_id
		 WHERE i.id = $1`

	var item dominio.ItemLista
	err := r.pool.QueryRow(ctx, consulta, itemID).Scan(
		&item.ID, &item.ListaID, &item.ProdutoID, &item.ProdutoNome,
		&item.MarcaID, &item.MarcaNome, &item.Quantidade, &item.Unidade,
	)
	if err != nil {
		return dominio.ItemLista{}, fmt.Errorf("buscar item: %w", traduzirErro(err, ""))
	}
	return item, nil
}

// RemoverItem apaga um item da lista informada. O filtro por lista_id impede
// que um id de item de outra lista seja removido por engano.
func (r *Repositorio) RemoverItem(ctx context.Context, listaID, itemID int64) error {
	etiqueta, err := r.pool.Exec(
		ctx, `DELETE FROM itens_lista WHERE id = $1 AND lista_id = $2`, itemID, listaID)
	if err != nil {
		return fmt.Errorf("remover item: %w", err)
	}
	if etiqueta.RowsAffected() == 0 {
		return dominio.ErrNaoEncontrado
	}
	return nil
}
