package servico

import (
	"encoding/json"
	"testing"

	"github.com/tcc/sad-compras/api/internal/dominio"
	"github.com/tcc/sad-compras/api/internal/otimizador"
)

func ponteiroDecimal(valor float64) *float64 { return &valor }

func TestResolverPesoTraduzOsTresPerfis(t *testing.T) {
	casos := map[string]float64{
		dominio.PerfilEconomico:   0.0,
		dominio.PerfilEquilibrado: 1.0,
		dominio.PerfilConveniente: 3.0,
	}

	for perfil, esperado := range casos {
		peso, nome, err := resolverPeso(PedidoRecomendacao{Perfil: perfil})
		if err != nil {
			t.Fatalf("perfil %q devolveu erro: %v", perfil, err)
		}
		if peso != esperado {
			t.Errorf("perfil %q gerou peso %v; esperado %v", perfil, peso, esperado)
		}
		if nome != perfil {
			t.Errorf("perfil devolvido = %q; esperado %q", nome, perfil)
		}
	}
}

// O peso numérico livre existe para os experimentos da Fase 4 e precisa
// prevalecer sobre o perfil quando os dois vêm no mesmo pedido.
func TestPesoExplicitoSobrepoePerfil(t *testing.T) {
	peso, _, err := resolverPeso(PedidoRecomendacao{
		Perfil:           dominio.PerfilConveniente,
		PesoConveniencia: ponteiroDecimal(0.25),
	})
	if err != nil {
		t.Fatalf("erro inesperado: %v", err)
	}
	if peso != 0.25 {
		t.Errorf("peso = %v; esperado 0.25", peso)
	}
}

func TestPesoLivreSemPerfilNomeadoNaoInventaRotulo(t *testing.T) {
	_, nome, err := resolverPeso(PedidoRecomendacao{PesoConveniencia: ponteiroDecimal(1.7)})
	if err != nil {
		t.Fatalf("erro inesperado: %v", err)
	}
	if nome != "" {
		t.Errorf("perfil = %q; esperado string vazia para peso livre", nome)
	}
}

func TestResolverPesoExigePerfilOuPeso(t *testing.T) {
	if _, _, err := resolverPeso(PedidoRecomendacao{}); err == nil {
		t.Error("pedido sem perfil e sem peso deveria ser rejeitado")
	}
}

func TestResolverPesoRejeitaPesoNegativo(t *testing.T) {
	_, _, err := resolverPeso(PedidoRecomendacao{PesoConveniencia: ponteiroDecimal(-1)})
	if err == nil {
		t.Error("peso negativo deveria ser rejeitado")
	}
}

func TestOrigemAusenteUsaPadraoEMarcaComoAproximada(t *testing.T) {
	servico := &Recomendacao{origemLat: -7.2131, origemLon: -39.3153}

	origem, aproximada := servico.resolverOrigem(nil)
	if !aproximada {
		t.Error("origem ausente deveria ser marcada como aproximada")
	}
	if origem.Latitude != -7.2131 || origem.Longitude != -39.3153 {
		t.Errorf("origem padrão = %+v; esperado o centro de Juazeiro do Norte", origem)
	}

	informada := &Coordenada{Latitude: -7.2470, Longitude: -39.3460}
	origem, aproximada = servico.resolverOrigem(informada)
	if aproximada {
		t.Error("origem informada não deveria ser marcada como aproximada")
	}
	if origem.Latitude != informada.Latitude {
		t.Errorf("origem = %+v; esperada a informada pelo cliente", origem)
	}
}

// Com marca livre, várias marcas do mesmo produto concorrem no mesmo mercado,
// mas o contrato admite um único candidato por par (item, mercado).
func TestMelhorCandidatoPrefereQuemAtendeAQuantidade(t *testing.T) {
	barataSemEstoque := otimizador.CandidatoRequisicao{
		PrecoUnitarioCentavos: 500, QuantidadeDisponivel: 1,
	}
	caraComEstoque := otimizador.CandidatoRequisicao{
		PrecoUnitarioCentavos: 900, QuantidadeDisponivel: 10,
	}

	if !melhorCandidato(caraComEstoque, barataSemEstoque, 5) {
		t.Error("a marca com estoque suficiente deveria vencer a mais barata sem estoque")
	}
	if melhorCandidato(barataSemEstoque, caraComEstoque, 5) {
		t.Error("a marca sem estoque não deveria substituir a que atende")
	}
}

func TestMelhorCandidatoDesempataPeloPreco(t *testing.T) {
	barata := otimizador.CandidatoRequisicao{
		PrecoUnitarioCentavos: 500, QuantidadeDisponivel: 10,
	}
	cara := otimizador.CandidatoRequisicao{
		PrecoUnitarioCentavos: 900, QuantidadeDisponivel: 10,
	}

	if !melhorCandidato(barata, cara, 5) {
		t.Error("entre duas marcas que atendem, a mais barata deveria vencer")
	}
}

// O payload precisa ser determinístico: a ordem dos candidatos não pode depender
// da iteração de mapa do Go.
func TestCandidatosSaemOrdenadosPorMercado(t *testing.T) {
	porMercado := map[int64]otimizador.CandidatoRequisicao{
		5: {MercadoID: 5},
		1: {MercadoID: 1},
		3: {MercadoID: 3},
	}

	for repeticao := 0; repeticao < 20; repeticao++ {
		ordenados := converterMercadosOrdenados(porMercado)
		identificadores := []int64{
			ordenados[0].MercadoID, ordenados[1].MercadoID, ordenados[2].MercadoID,
		}
		if identificadores[0] != 1 || identificadores[1] != 3 || identificadores[2] != 5 {
			t.Fatalf("ordem inesperada: %v", identificadores)
		}
	}
}

func TestMontarRespostaEnriquecComNomesEEndereco(t *testing.T) {
	lista := dominio.Lista{
		ID: 3,
		Itens: []dominio.ItemLista{
			{ID: 10, ProdutoNome: "Arroz"},
			{ID: 11, ProdutoNome: "Café"},
		},
	}
	mercados := []dominio.Mercado{
		{ID: 1, Nome: "Mercado Central do Juazeiro", Endereco: "R. São Pedro, 210 - Centro"},
	}
	resposta := otimizador.Resposta{
		Status:             "OTIMO",
		CustoTotalCentavos: 5198,
		ComprasPorMercado: []otimizador.CompraMercado{{
			MercadoID: 1,
			Nome:      "Mercado Central do Juazeiro",
			Itens: []otimizador.ItemComprado{{
				ItemID: 10, MarcaNome: "Marca A", Quantidade: 2, Unidade: "un",
			}},
		}},
		ItensNaoAtendidos: []otimizador.ItemNaoAtendido{{
			ItemID: 11, Motivo: "SEM_CANDIDATO",
		}},
		Economia: json.RawMessage(`{"economia_centavos":100}`),
	}

	gerada := montarResposta(resposta, lista, mercados)

	if gerada.ComprasPorMercado[0].Endereco != "R. São Pedro, 210 - Centro" {
		t.Errorf("endereço não foi anexado: %q", gerada.ComprasPorMercado[0].Endereco)
	}
	if gerada.ComprasPorMercado[0].Itens[0].ProdutoNome != "Arroz" {
		t.Errorf("nome do produto não foi anexado: %q",
			gerada.ComprasPorMercado[0].Itens[0].ProdutoNome)
	}
	if gerada.ItensNaoAtendidos[0].ProdutoNome != "Café" {
		t.Errorf("nome do produto não atendido não foi anexado: %q",
			gerada.ItensNaoAtendidos[0].ProdutoNome)
	}
}

// Listas sem alocação precisam serializar como [] e não como null, para que o
// PWA não tenha de tratar dois casos diferentes.
func TestListasVaziasSerializamComoArranjo(t *testing.T) {
	gerada := montarResposta(otimizador.Resposta{}, dominio.Lista{}, nil)

	corpo, err := json.Marshal(gerada)
	if err != nil {
		t.Fatalf("erro ao serializar: %v", err)
	}

	var decodificado map[string]any
	if err := json.Unmarshal(corpo, &decodificado); err != nil {
		t.Fatalf("erro ao decodificar: %v", err)
	}

	for _, campo := range []string{"rota", "compras_por_mercado", "itens_nao_atendidos"} {
		if decodificado[campo] == nil {
			t.Errorf("campo %q veio null; esperado arranjo vazio", campo)
		}
	}
}

func TestConverterMercadosPreservaCoordenadas(t *testing.T) {
	mercados := []dominio.Mercado{
		{ID: 5, Nome: "Atacadão do Limoeiro", Latitude: -7.247, Longitude: -39.346},
	}

	convertidos := converterMercados(mercados)

	if len(convertidos) != 1 {
		t.Fatalf("esperado 1 mercado; obtido %d", len(convertidos))
	}
	if convertidos[0].MercadoID != 5 || convertidos[0].Latitude != -7.247 {
		t.Errorf("conversão perdeu dados: %+v", convertidos[0])
	}
}
