package servico

import (
	"context"
	"strings"

	"github.com/tcc/sad-compras/api/internal/dominio"
	"github.com/tcc/sad-compras/api/internal/repositorio"
)

// Lista cuida das listas de compra e de seus itens, sempre escopadas ao dono.
type Lista struct {
	repositorio *repositorio.Repositorio
}

// NovaLista monta o serviço de listas.
func NovaLista(repo *repositorio.Repositorio) *Lista {
	return &Lista{repositorio: repo}
}

// garantirPosse carrega a lista e confirma que ela pertence ao usuário.
//
// Devolve ErrNaoAutorizado (403), e não ErrNaoEncontrado (404), quando a lista
// existe mas é de outro usuário: o contrato REST define esse comportamento.
func (l *Lista) garantirPosse(
	ctx context.Context, listaID, usuarioID int64,
) (dominio.Lista, error) {
	lista, err := l.repositorio.BuscarLista(ctx, listaID)
	if err != nil {
		return dominio.Lista{}, err
	}
	if lista.UsuarioID != usuarioID {
		return dominio.Lista{}, dominio.ErrNaoAutorizado
	}
	return lista, nil
}

// Listar devolve as listas do usuário com a contagem de itens.
func (l *Lista) Listar(ctx context.Context, usuarioID int64) ([]dominio.Lista, error) {
	return l.repositorio.ListarListasDoUsuario(ctx, usuarioID)
}

// Criar abre uma lista vazia.
func (l *Lista) Criar(
	ctx context.Context, usuarioID int64, nome string,
) (dominio.Lista, error) {
	nome = strings.TrimSpace(nome)
	if nome == "" {
		return dominio.Lista{}, dominio.NovoErroValidacao("nome da lista é obrigatório")
	}
	return l.repositorio.CriarLista(ctx, usuarioID, nome)
}

// Buscar devolve a lista com os itens expandidos.
func (l *Lista) Buscar(
	ctx context.Context, listaID, usuarioID int64,
) (dominio.Lista, error) {
	lista, err := l.garantirPosse(ctx, listaID, usuarioID)
	if err != nil {
		return dominio.Lista{}, err
	}

	itens, err := l.repositorio.ListarItens(ctx, listaID)
	if err != nil {
		return dominio.Lista{}, err
	}
	lista.Itens = itens
	lista.QuantidadeItens = len(itens)
	return lista, nil
}

// Renomear altera o nome da lista.
func (l *Lista) Renomear(
	ctx context.Context, listaID, usuarioID int64, nome string,
) (dominio.Lista, error) {
	if _, err := l.garantirPosse(ctx, listaID, usuarioID); err != nil {
		return dominio.Lista{}, err
	}
	nome = strings.TrimSpace(nome)
	if nome == "" {
		return dominio.Lista{}, dominio.NovoErroValidacao("nome da lista é obrigatório")
	}
	return l.repositorio.AtualizarLista(ctx, listaID, nome)
}

// Remover apaga a lista; itens e recomendações caem em cascata.
func (l *Lista) Remover(ctx context.Context, listaID, usuarioID int64) error {
	if _, err := l.garantirPosse(ctx, listaID, usuarioID); err != nil {
		return err
	}
	return l.repositorio.RemoverLista(ctx, listaID)
}

// validarItem aplica as regras comuns a inclusão e alteração de item.
func validarItem(produtoID int64, quantidade float64, unidade string) error {
	if produtoID <= 0 {
		return dominio.NovoErroValidacao("produto_id é obrigatório")
	}
	if quantidade <= 0 {
		return dominio.NovoErroValidacao("quantidade deve ser maior que zero")
	}
	return dominio.ValidarUnidade(unidade)
}

// AdicionarItem inclui um item na lista. MarcaID nulo significa "qualquer
// marca serve", o que costuma gerar mais economia na recomendação.
func (l *Lista) AdicionarItem(
	ctx context.Context,
	listaID, usuarioID, produtoID int64,
	marcaID *int64,
	quantidade float64,
	unidade string,
) (dominio.ItemLista, error) {
	if _, err := l.garantirPosse(ctx, listaID, usuarioID); err != nil {
		return dominio.ItemLista{}, err
	}
	if err := validarItem(produtoID, quantidade, unidade); err != nil {
		return dominio.ItemLista{}, err
	}
	return l.repositorio.AdicionarItem(ctx, listaID, produtoID, marcaID, quantidade, unidade)
}

// AtualizarItem altera um item existente, conferindo que ele pertence à lista.
func (l *Lista) AtualizarItem(
	ctx context.Context,
	listaID, usuarioID, itemID, produtoID int64,
	marcaID *int64,
	quantidade float64,
	unidade string,
) (dominio.ItemLista, error) {
	if _, err := l.garantirPosse(ctx, listaID, usuarioID); err != nil {
		return dominio.ItemLista{}, err
	}
	if err := validarItem(produtoID, quantidade, unidade); err != nil {
		return dominio.ItemLista{}, err
	}

	item, err := l.repositorio.BuscarItem(ctx, itemID)
	if err != nil {
		return dominio.ItemLista{}, err
	}
	if item.ListaID != listaID {
		return dominio.ItemLista{}, dominio.ErrNaoEncontrado
	}
	return l.repositorio.AtualizarItem(ctx, itemID, produtoID, marcaID, quantidade, unidade)
}

// RemoverItem exclui um item da lista.
func (l *Lista) RemoverItem(ctx context.Context, listaID, usuarioID, itemID int64) error {
	if _, err := l.garantirPosse(ctx, listaID, usuarioID); err != nil {
		return err
	}
	return l.repositorio.RemoverItem(ctx, listaID, itemID)
}
