package dominio

import "time"

// UnidadesValidas espelha o CHECK de `precos.unidade` e `itens_lista.unidade`
// no esquema do banco. Validar aqui evita depender do erro 23514 do Postgres
// para produzir uma mensagem legível.
var UnidadesValidas = []string{"kg", "g", "L", "ml", "un"}

// ValidarUnidade rejeita unidades fora do CHECK do banco.
func ValidarUnidade(unidade string) error {
	for _, valida := range UnidadesValidas {
		if unidade == valida {
			return nil
		}
	}
	return NovoErroValidacao("unidade inválida: %q; use kg, g, L, ml ou un", unidade)
}

// Usuario é o dono das listas de compra.
type Usuario struct {
	ID        int64     `json:"id"`
	Nome      string    `json:"nome"`
	Email     string    `json:"email"`
	SenhaHash string    `json:"-"`
	CriadoEm  time.Time `json:"criado_em"`
}

// Produto é o item genérico da cesta, sem marca.
type Produto struct {
	ID        int64     `json:"id"`
	Nome      string    `json:"nome"`
	Categoria string    `json:"categoria"`
	CriadoEm  time.Time `json:"criado_em"`
}

// Marca é a variante comercial concreta de um produto.
type Marca struct {
	ID        int64     `json:"id"`
	ProdutoID int64     `json:"produto_id"`
	Nome      string    `json:"nome"`
	CriadoEm  time.Time `json:"criado_em"`
}

// Mercado é um supermercado do recorte geográfico da PoC.
type Mercado struct {
	ID        int64     `json:"id"`
	Nome      string    `json:"nome"`
	Latitude  float64   `json:"latitude"`
	Longitude float64   `json:"longitude"`
	Endereco  string    `json:"endereco"`
	CriadoEm  time.Time `json:"criado_em"`
}

// Preco é um snapshot de preço e disponibilidade. O valor monetário sai da API
// em centavos inteiros, conforme o contrato REST.
type Preco struct {
	ID                   int64     `json:"id"`
	MarcaID              int64     `json:"marca_id"`
	MercadoID            int64     `json:"mercado_id"`
	PrecoCentavos        int64     `json:"preco_centavos"`
	Unidade              string    `json:"unidade"`
	QuantidadeDisponivel float64   `json:"quantidade_disponivel"`
	ColetadoEm           time.Time `json:"coletado_em"`
	MarcaNome            string    `json:"marca_nome,omitempty"`
	MercadoNome          string    `json:"mercado_nome,omitempty"`
}

// Lista é uma lista de compras de um usuário.
type Lista struct {
	ID              int64       `json:"id"`
	UsuarioID       int64       `json:"usuario_id"`
	Nome            string      `json:"nome"`
	CriadoEm        time.Time   `json:"criado_em"`
	QuantidadeItens int         `json:"quantidade_itens"`
	Itens           []ItemLista `json:"itens,omitempty"`
}

// ItemLista é um item pedido dentro de uma lista, já com produto e marca
// resolvidos para exibição. MarcaID nulo significa indiferença de marca.
type ItemLista struct {
	ID          int64   `json:"id"`
	ListaID     int64   `json:"lista_id"`
	ProdutoID   int64   `json:"produto_id"`
	ProdutoNome string  `json:"produto_nome"`
	MarcaID     *int64  `json:"marca_id"`
	MarcaNome   *string `json:"marca_nome"`
	Quantidade  float64 `json:"quantidade"`
	Unidade     string  `json:"unidade"`
}

// CandidatoPreco é uma oferta vigente capaz de atender um item da lista.
// Vem da view `precos_vigentes`, nunca da tabela `precos`.
type CandidatoPreco struct {
	ItemID                int64
	MercadoID             int64
	MarcaID               int64
	MarcaNome             string
	PrecoUnitarioCentavos int64
	QuantidadeDisponivel  float64
	Unidade               string
}

// ResumoRecomendacao é a linha do histórico de recomendações de uma lista.
type ResumoRecomendacao struct {
	ID                 int64     `json:"id"`
	ListaID            int64     `json:"lista_id"`
	GeradoEm           time.Time `json:"gerado_em"`
	CustoTotalCentavos int64     `json:"custo_total_centavos"`
	PesoConveniencia   float64   `json:"peso_conveniencia"`
	Perfil             string    `json:"perfil"`
}
