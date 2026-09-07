package servico

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/tcc/sad-compras/api/internal/dominio"
	"github.com/tcc/sad-compras/api/internal/otimizador"
	"github.com/tcc/sad-compras/api/internal/repositorio"
)

// Tetos da PoC, declarados no contrato REST e nos requisitos não funcionais.
// Instâncias acima disso são rejeitadas, nunca processadas parcialmente.
const (
	MaximoItensPorLista = 20
	MaximoMercados      = 8
)

// Recomendacao orquestra a geração de uma recomendação: lê o banco, monta o
// payload do otimizador, chama o serviço Python, persiste o resultado e o
// formata para o cliente.
//
// É o único ponto do sistema que conhece os dois contratos ao mesmo tempo.
type Recomendacao struct {
	repositorio *repositorio.Repositorio
	lista       *Lista
	cliente     *otimizador.Cliente
	origemLat   float64
	origemLon   float64
}

// NovaRecomendacao monta o serviço com a coordenada de origem padrão.
func NovaRecomendacao(
	repo *repositorio.Repositorio,
	servicoLista *Lista,
	cliente *otimizador.Cliente,
	origemLatitude, origemLongitude float64,
) *Recomendacao {
	return &Recomendacao{
		repositorio: repo,
		lista:       servicoLista,
		cliente:     cliente,
		origemLat:   origemLatitude,
		origemLon:   origemLongitude,
	}
}

// PedidoRecomendacao é o corpo de POST /listas/:id/recomendacoes.
type PedidoRecomendacao struct {
	Perfil           string      `json:"perfil"`
	PesoConveniencia *float64    `json:"peso_conveniencia"`
	Origem           *Coordenada `json:"origem"`
}

// Coordenada é o ponto de partida e retorno do usuário.
type Coordenada struct {
	Latitude  float64 `json:"latitude"`
	Longitude float64 `json:"longitude"`
}

// ItemRecomendado é um item já alocado a um mercado, enriquecido com os nomes
// que o otimizador não conhece.
type ItemRecomendado struct {
	ItemID                int64   `json:"item_id"`
	ProdutoNome           string  `json:"produto_nome"`
	MarcaNome             string  `json:"marca_nome"`
	Quantidade            float64 `json:"quantidade"`
	Unidade               string  `json:"unidade"`
	PrecoUnitarioCentavos int64   `json:"preco_unitario_centavos"`
	CustoCentavos         int64   `json:"custo_centavos"`
}

// CompraNoMercado é o que comprar em um mercado, na ordem da rota.
type CompraNoMercado struct {
	MercadoID        int64             `json:"mercado_id"`
	Nome             string            `json:"nome"`
	Endereco         string            `json:"endereco"`
	SubtotalCentavos int64             `json:"subtotal_centavos"`
	Itens            []ItemRecomendado `json:"itens"`
}

// ItemSemAtendimento é um item que nenhum mercado pôde atender.
type ItemSemAtendimento struct {
	ItemID      int64  `json:"item_id"`
	ProdutoNome string `json:"produto_nome"`
	Motivo      string `json:"motivo"`
}

// RecomendacaoGerada é a resposta do contrato REST.
type RecomendacaoGerada struct {
	ID                          int64                   `json:"id"`
	ListaID                     int64                   `json:"lista_id"`
	GeradoEm                    time.Time               `json:"gerado_em"`
	Perfil                      string                  `json:"perfil"`
	PesoConveniencia            float64                 `json:"peso_conveniencia"`
	OrigemAproximada            bool                    `json:"origem_aproximada"`
	Status                      string                  `json:"status"`
	CustoItensCentavos          int64                   `json:"custo_itens_centavos"`
	CustoLogisticoCentavos      int64                   `json:"custo_logistico_centavos"`
	CustoTotalCentavos          int64                   `json:"custo_total_centavos"`
	QuantidadeMercadosVisitados int                     `json:"quantidade_mercados_visitados"`
	DistanciaTotalKm            float64                 `json:"distancia_total_km"`
	Rota                        []otimizador.ParadaRota `json:"rota"`
	ComprasPorMercado           []CompraNoMercado       `json:"compras_por_mercado"`
	ItensNaoAtendidos           []ItemSemAtendimento    `json:"itens_nao_atendidos"`
	Economia                    json.RawMessage         `json:"economia"`
}

// Gerar produz uma nova recomendação para a lista.
//
// A sequência é a descrita em docs/arquitetura.md: conferir posse, carregar
// itens e ofertas vigentes, montar o payload em centavos, chamar o otimizador,
// persistir o resultado bruto para auditoria e devolver a resposta formatada.
func (r *Recomendacao) Gerar(
	ctx context.Context, listaID, usuarioID int64, pedido PedidoRecomendacao,
) (RecomendacaoGerada, error) {
	lista, err := r.lista.Buscar(ctx, listaID, usuarioID)
	if err != nil {
		return RecomendacaoGerada{}, err
	}

	peso, perfil, err := resolverPeso(pedido)
	if err != nil {
		return RecomendacaoGerada{}, err
	}

	if len(lista.Itens) > MaximoItensPorLista {
		return RecomendacaoGerada{}, dominio.NovoErroValidacao(
			"a lista tem %d itens; o teto da PoC é %d",
			len(lista.Itens), MaximoItensPorLista)
	}

	mercados, err := r.repositorio.ListarMercados(ctx)
	if err != nil {
		return RecomendacaoGerada{}, err
	}
	if len(mercados) > MaximoMercados {
		return RecomendacaoGerada{}, dominio.NovoErroValidacao(
			"há %d mercados cadastrados; o teto da PoC é %d", len(mercados), MaximoMercados)
	}

	origem, aproximada := r.resolverOrigem(pedido.Origem)

	requisicao := otimizador.Requisicao{
		Origem:           origem,
		PesoConveniencia: peso,
		Mercados:         converterMercados(mercados),
	}
	if requisicao.Itens, err = r.montarItens(ctx, lista.Itens); err != nil {
		return RecomendacaoGerada{}, err
	}

	resposta, err := r.cliente.Otimizar(ctx, requisicao)
	if err != nil {
		return RecomendacaoGerada{}, err
	}

	registro, err := r.repositorio.SalvarRecomendacao(
		ctx, listaID, resposta.CustoTotalCentavos, peso, resposta.Bruto)
	if err != nil {
		return RecomendacaoGerada{}, err
	}

	gerada := montarResposta(resposta, lista, mercados)
	gerada.ID = registro.ID
	gerada.ListaID = listaID
	gerada.GeradoEm = registro.GeradoEm
	gerada.Perfil = perfil
	gerada.PesoConveniencia = peso
	gerada.OrigemAproximada = aproximada
	return gerada, nil
}

// resolverPeso decide o peso da parcela logística. Um peso numérico explícito
// sobrepõe o perfil — é o que permite varrer a fronteira de Pareto nos
// experimentos da Fase 4 sem alterar código.
func resolverPeso(pedido PedidoRecomendacao) (float64, string, error) {
	if pedido.PesoConveniencia != nil {
		peso := *pedido.PesoConveniencia
		if peso < 0 {
			return 0, "", dominio.NovoErroValidacao(
				"peso_conveniencia não pode ser negativo")
		}
		return peso, dominio.PerfilDoPeso(peso), nil
	}
	if pedido.Perfil == "" {
		return 0, "", dominio.NovoErroValidacao(
			"informe perfil (economico, equilibrado ou conveniente) ou peso_conveniencia")
	}
	peso, err := dominio.PesoDoPerfil(pedido.Perfil)
	if err != nil {
		return 0, "", err
	}
	return peso, pedido.Perfil, nil
}

// resolverOrigem usa a coordenada enviada pelo cliente ou, na ausência dela, a
// referência configurada no servidor — sinalizando que a distância é aproximada.
func (r *Recomendacao) resolverOrigem(informada *Coordenada) (otimizador.Coordenada, bool) {
	if informada != nil {
		return otimizador.Coordenada{
			Latitude:  informada.Latitude,
			Longitude: informada.Longitude,
		}, false
	}
	return otimizador.Coordenada{Latitude: r.origemLat, Longitude: r.origemLon}, true
}

// converterMercados traduz os mercados do domínio para o contrato do otimizador.
func converterMercados(mercados []dominio.Mercado) []otimizador.MercadoRequisicao {
	convertidos := make([]otimizador.MercadoRequisicao, 0, len(mercados))
	for _, mercado := range mercados {
		convertidos = append(convertidos, otimizador.MercadoRequisicao{
			MercadoID: mercado.ID,
			Nome:      mercado.Nome,
			Latitude:  mercado.Latitude,
			Longitude: mercado.Longitude,
		})
	}
	return convertidos
}

// montarItens transforma os itens da lista nos itens do payload de otimização,
// anexando a cada um os candidatos vindos de precos_vigentes.
//
// Quando o item fixa uma marca, só ela é candidata; quando a marca é nula,
// qualquer marca do produto pode atender. Candidatos com estoque insuficiente
// são enviados assim mesmo: descartá-los é responsabilidade do otimizador, que
// precisa distinguir "sem preço" de "sem estoque" no motivo de não atendimento.
func (r *Recomendacao) montarItens(
	ctx context.Context, itens []dominio.ItemLista,
) ([]otimizador.ItemRequisicao, error) {
	if len(itens) == 0 {
		return []otimizador.ItemRequisicao{}, nil
	}

	produtoIDs := make([]int64, 0, len(itens))
	vistos := make(map[int64]bool, len(itens))
	for _, item := range itens {
		if !vistos[item.ProdutoID] {
			vistos[item.ProdutoID] = true
			produtoIDs = append(produtoIDs, item.ProdutoID)
		}
	}

	ofertas, err := r.repositorio.BuscarOfertasVigentes(ctx, produtoIDs)
	if err != nil {
		return nil, fmt.Errorf("montar candidatos da otimização: %w", err)
	}

	ofertasPorProduto := make(map[int64][]repositorio.OfertaVigente, len(produtoIDs))
	for _, oferta := range ofertas {
		ofertasPorProduto[oferta.ProdutoID] = append(ofertasPorProduto[oferta.ProdutoID], oferta)
	}

	convertidos := make([]otimizador.ItemRequisicao, 0, len(itens))
	for _, item := range itens {
		candidatos := make([]otimizador.CandidatoRequisicao, 0)
		melhorPorMercado := make(map[int64]otimizador.CandidatoRequisicao)

		for _, oferta := range ofertasPorProduto[item.ProdutoID] {
			if item.MarcaID != nil && oferta.MarcaID != *item.MarcaID {
				continue
			}
			candidato := otimizador.CandidatoRequisicao{
				MercadoID:             oferta.MercadoID,
				MarcaID:               oferta.MarcaID,
				MarcaNome:             oferta.MarcaNome,
				PrecoUnitarioCentavos: oferta.PrecoUnitarioCentavos,
				QuantidadeDisponivel:  oferta.QuantidadeDisponivel,
			}
			// O contrato admite um único candidato por par (item, mercado).
			// Com marca livre, várias marcas do mesmo produto concorrem no
			// mesmo mercado: prevalece a que atende o pedido mais barato.
			atual, existe := melhorPorMercado[oferta.MercadoID]
			if !existe || melhorCandidato(candidato, atual, item.Quantidade) {
				melhorPorMercado[oferta.MercadoID] = candidato
			}
		}

		for _, mercado := range converterMercadosOrdenados(melhorPorMercado) {
			candidatos = append(candidatos, mercado)
		}

		convertidos = append(convertidos, otimizador.ItemRequisicao{
			ItemID:     item.ID,
			Descricao:  item.ProdutoNome,
			Quantidade: item.Quantidade,
			Unidade:    item.Unidade,
			Candidatos: candidatos,
		})
	}
	return convertidos, nil
}

// melhorCandidato decide entre duas marcas do mesmo produto no mesmo mercado.
// Uma marca que atende a quantidade pedida sempre vence uma que não atende;
// entre duas equivalentes nesse critério, vence a mais barata.
func melhorCandidato(
	novo, atual otimizador.CandidatoRequisicao, quantidade float64,
) bool {
	novoAtende := novo.QuantidadeDisponivel >= quantidade
	atualAtende := atual.QuantidadeDisponivel >= quantidade
	if novoAtende != atualAtende {
		return novoAtende
	}
	return novo.PrecoUnitarioCentavos < atual.PrecoUnitarioCentavos
}

// converterMercadosOrdenados devolve os candidatos em ordem estável de
// mercado_id, para que o payload enviado ao otimizador seja determinístico.
func converterMercadosOrdenados(
	porMercado map[int64]otimizador.CandidatoRequisicao,
) []otimizador.CandidatoRequisicao {
	identificadores := make([]int64, 0, len(porMercado))
	for mercadoID := range porMercado {
		identificadores = append(identificadores, mercadoID)
	}
	for i := 1; i < len(identificadores); i++ {
		for j := i; j > 0 && identificadores[j] < identificadores[j-1]; j-- {
			identificadores[j], identificadores[j-1] = identificadores[j-1], identificadores[j]
		}
	}

	ordenados := make([]otimizador.CandidatoRequisicao, 0, len(identificadores))
	for _, mercadoID := range identificadores {
		ordenados = append(ordenados, porMercado[mercadoID])
	}
	return ordenados
}

// montarResposta enriquece o resultado do otimizador com endereço do mercado e
// nome do produto, que o serviço Python não conhece.
func montarResposta(
	resposta otimizador.Resposta, lista dominio.Lista, mercados []dominio.Mercado,
) RecomendacaoGerada {
	enderecoPorMercado := make(map[int64]string, len(mercados))
	for _, mercado := range mercados {
		enderecoPorMercado[mercado.ID] = mercado.Endereco
	}
	produtoPorItem := make(map[int64]string, len(lista.Itens))
	for _, item := range lista.Itens {
		produtoPorItem[item.ID] = item.ProdutoNome
	}

	compras := make([]CompraNoMercado, 0, len(resposta.ComprasPorMercado))
	for _, compra := range resposta.ComprasPorMercado {
		itens := make([]ItemRecomendado, 0, len(compra.Itens))
		for _, item := range compra.Itens {
			itens = append(itens, ItemRecomendado{
				ItemID:                item.ItemID,
				ProdutoNome:           produtoPorItem[item.ItemID],
				MarcaNome:             item.MarcaNome,
				Quantidade:            item.Quantidade,
				Unidade:               item.Unidade,
				PrecoUnitarioCentavos: item.PrecoUnitarioCentavos,
				CustoCentavos:         item.CustoCentavos,
			})
		}
		compras = append(compras, CompraNoMercado{
			MercadoID:        compra.MercadoID,
			Nome:             compra.Nome,
			Endereco:         enderecoPorMercado[compra.MercadoID],
			SubtotalCentavos: compra.SubtotalCentavos,
			Itens:            itens,
		})
	}

	naoAtendidos := make([]ItemSemAtendimento, 0, len(resposta.ItensNaoAtendidos))
	for _, item := range resposta.ItensNaoAtendidos {
		naoAtendidos = append(naoAtendidos, ItemSemAtendimento{
			ItemID:      item.ItemID,
			ProdutoNome: produtoPorItem[item.ItemID],
			Motivo:      item.Motivo,
		})
	}

	rota := resposta.Rota
	if rota == nil {
		rota = []otimizador.ParadaRota{}
	}

	return RecomendacaoGerada{
		Status:                      resposta.Status,
		CustoItensCentavos:          resposta.CustoItensCentavos,
		CustoLogisticoCentavos:      resposta.CustoLogisticoCentavos,
		CustoTotalCentavos:          resposta.CustoTotalCentavos,
		QuantidadeMercadosVisitados: resposta.QuantidadeMercadosVisitados,
		DistanciaTotalKm:            resposta.DistanciaTotalKm,
		Rota:                        rota,
		ComprasPorMercado:           compras,
		ItensNaoAtendidos:           naoAtendidos,
		Economia:                    resposta.Economia,
	}
}

// ListarHistorico devolve as recomendações já geradas para a lista.
func (r *Recomendacao) ListarHistorico(
	ctx context.Context, listaID, usuarioID int64,
) ([]dominio.ResumoRecomendacao, error) {
	if _, err := r.lista.Buscar(ctx, listaID, usuarioID); err != nil {
		return nil, err
	}
	return r.repositorio.ListarRecomendacoesDaLista(ctx, listaID)
}

// Buscar devolve uma recomendação já gerada, reconstruída a partir do payload
// gravado. Reabrir o histórico nunca recalcula: a recomendação é imutável, e é
// isso que permite comparar execuções na avaliação de acurácia da Fase 4.
func (r *Recomendacao) Buscar(
	ctx context.Context, recomendacaoID, usuarioID int64,
) (RecomendacaoGerada, error) {
	registro, err := r.repositorio.BuscarRecomendacao(ctx, recomendacaoID)
	if err != nil {
		return RecomendacaoGerada{}, err
	}

	lista, err := r.lista.Buscar(ctx, registro.ListaID, usuarioID)
	if err != nil {
		return RecomendacaoGerada{}, err
	}

	var resposta otimizador.Resposta
	if err := json.Unmarshal(registro.Payload, &resposta); err != nil {
		return RecomendacaoGerada{}, fmt.Errorf("interpretar payload persistido: %w", err)
	}

	mercados, err := r.repositorio.ListarMercados(ctx)
	if err != nil {
		return RecomendacaoGerada{}, err
	}

	gerada := montarResposta(resposta, lista, mercados)
	gerada.ID = registro.ID
	gerada.ListaID = registro.ListaID
	gerada.GeradoEm = registro.GeradoEm
	gerada.PesoConveniencia = registro.PesoConveniencia
	gerada.Perfil = dominio.PerfilDoPeso(registro.PesoConveniencia)
	return gerada, nil
}
