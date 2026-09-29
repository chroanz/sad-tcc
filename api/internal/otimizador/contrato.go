// Package otimizador implementa o cliente HTTP do serviço Python de otimização
// (FastAPI + OR-Tools CP-SAT), conforme docs/contrato-otimizacao.md.
package otimizador

import "encoding/json"

// Coordenada é um par latitude/longitude em graus decimais WGS84.
type Coordenada struct {
	Latitude  float64 `json:"latitude"`
	Longitude float64 `json:"longitude"`
}

// Requisicao é o corpo de POST /otimizar. Os campos opcionais do contrato
// (custo_por_visita_centavos e limite_tempo_segundos) são omitidos para que
// valham os padrões do serviço Python. Não há custo por quilômetro: a distância
// percorrida não é precificada.
type Requisicao struct {
	Origem           Coordenada          `json:"origem"`
	PesoConveniencia float64             `json:"peso_conveniencia"`
	Mercados         []MercadoRequisicao `json:"mercados"`
	Itens            []ItemRequisicao    `json:"itens"`
}

// MercadoRequisicao é um mercado candidato, com as coordenadas usadas para
// ordenar a visita (o mais próximo primeiro) e para o desempate do solver.
type MercadoRequisicao struct {
	MercadoID int64   `json:"mercado_id"`
	Nome      string  `json:"nome"`
	Latitude  float64 `json:"latitude"`
	Longitude float64 `json:"longitude"`
}

// ItemRequisicao é um item da lista de compras — o índice i das variáveis
// x[i][j] do modelo.
type ItemRequisicao struct {
	ItemID     int64                 `json:"item_id"`
	Descricao  string                `json:"descricao"`
	Quantidade float64               `json:"quantidade"`
	Unidade    string                `json:"unidade"`
	Candidatos []CandidatoRequisicao `json:"candidatos"`
}

// CandidatoRequisicao é uma oferta vigente de um item em um mercado.
type CandidatoRequisicao struct {
	MercadoID             int64   `json:"mercado_id"`
	MarcaID               int64   `json:"marca_id"`
	MarcaNome             string  `json:"marca_nome"`
	PrecoUnitarioCentavos int64   `json:"preco_unitario_centavos"`
	QuantidadeDisponivel  float64 `json:"quantidade_disponivel"`
}

// Resposta é o corpo de 200 OK de POST /otimizar.
type Resposta struct {
	Status                      string            `json:"status"`
	CustoItensCentavos          int64             `json:"custo_itens_centavos"`
	CustoLogisticoCentavos      int64             `json:"custo_logistico_centavos"`
	CustoTotalCentavos          int64             `json:"custo_total_centavos"`
	ValorObjetivoCentavos       int64             `json:"valor_objetivo_centavos"`
	PesoConveniencia            float64           `json:"peso_conveniencia"`
	CustoPorVisitaCentavos      int64             `json:"custo_por_visita_centavos"`
	QuantidadeMercadosVisitados int               `json:"quantidade_mercados_visitados"`
	DistanciaTotalKm            float64           `json:"distancia_total_km"`
	Rota                        []ParadaRota      `json:"rota"`
	ComprasPorMercado           []CompraMercado   `json:"compras_por_mercado"`
	ItensNaoAtendidos           []ItemNaoAtendido `json:"itens_nao_atendidos"`
	Economia                    json.RawMessage   `json:"economia"`
	Diagnostico                 json.RawMessage   `json:"diagnostico"`

	// Bruto guarda o corpo original da resposta, persistido em
	// recomendacoes.payload_resultado. Não faz parte do contrato HTTP.
	Bruto json.RawMessage `json:"-"`
}

// ParadaRota é um mercado na ordem sugerida de visita: a partir da origem,
// sempre o mais próximo ainda não visitado.
type ParadaRota struct {
	Ordem                 int     `json:"ordem"`
	MercadoID             int64   `json:"mercado_id"`
	Nome                  string  `json:"nome"`
	DistanciaDoAnteriorKm float64 `json:"distancia_do_anterior_km"`
}

// CompraMercado agrupa o que comprar em um mercado.
type CompraMercado struct {
	MercadoID        int64          `json:"mercado_id"`
	Nome             string         `json:"nome"`
	SubtotalCentavos int64          `json:"subtotal_centavos"`
	Itens            []ItemComprado `json:"itens"`
}

// ItemComprado é a alocação de um item a um mercado.
type ItemComprado struct {
	ItemID                int64   `json:"item_id"`
	Descricao             string  `json:"descricao"`
	MarcaID               int64   `json:"marca_id"`
	MarcaNome             string  `json:"marca_nome"`
	Quantidade            float64 `json:"quantidade"`
	Unidade               string  `json:"unidade"`
	PrecoUnitarioCentavos int64   `json:"preco_unitario_centavos"`
	CustoCentavos         int64   `json:"custo_centavos"`
}

// ItemNaoAtendido é um item sem alocação, com o motivo informado pelo solver
// (SEM_CANDIDATO ou SEM_CANDIDATO_COM_ESTOQUE).
type ItemNaoAtendido struct {
	ItemID    int64  `json:"item_id"`
	Descricao string `json:"descricao"`
	Motivo    string `json:"motivo"`
}
