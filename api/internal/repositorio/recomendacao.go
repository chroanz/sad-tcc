package repositorio

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/tcc/sad-compras/api/internal/dominio"
)

// RecomendacaoPersistida é o registro completo devolvido do banco, incluindo o
// payload bruto do otimizador. Reabrir uma recomendação nunca recalcula nada:
// o histórico é imutável, e é isso que o torna auditável na Fase 4.
type RecomendacaoPersistida struct {
	ID               int64
	ListaID          int64
	GeradoEm         time.Time
	PesoConveniencia float64
	Payload          json.RawMessage
}

// SalvarRecomendacao grava o resultado do otimizador para auditoria.
func (r *Repositorio) SalvarRecomendacao(
	ctx context.Context,
	listaID int64,
	custoTotalCentavos int64,
	pesoConveniencia float64,
	payload json.RawMessage,
) (RecomendacaoPersistida, error) {
	const consulta = `
		INSERT INTO recomendacoes (lista_id, custo_total, parametro_peso_conveniencia, payload_resultado)
		VALUES ($1, $2::numeric, $3, $4)
		RETURNING id, lista_id, gerado_em, parametro_peso_conveniencia::float8`

	var registro RecomendacaoPersistida
	err := r.pool.QueryRow(
		ctx, consulta, listaID,
		dominio.ConverterCentavosParaReais(custoTotalCentavos),
		pesoConveniencia, []byte(payload),
	).Scan(&registro.ID, &registro.ListaID, &registro.GeradoEm, &registro.PesoConveniencia)
	if err != nil {
		return RecomendacaoPersistida{}, fmt.Errorf(
			"salvar recomendação: %w", traduzirErro(err, ""))
	}
	registro.Payload = payload
	return registro, nil
}

// ListarRecomendacoesDaLista devolve o histórico resumido, mais recente
// primeiro.
func (r *Repositorio) ListarRecomendacoesDaLista(
	ctx context.Context, listaID int64,
) ([]dominio.ResumoRecomendacao, error) {
	const consulta = `
		SELECT id, lista_id, gerado_em, custo_total::text, parametro_peso_conveniencia::float8
		  FROM recomendacoes
		 WHERE lista_id = $1
		 ORDER BY gerado_em DESC, id DESC`

	linhas, err := r.pool.Query(ctx, consulta, listaID)
	if err != nil {
		return nil, fmt.Errorf("listar recomendações: %w", err)
	}
	defer linhas.Close()

	resumos := make([]dominio.ResumoRecomendacao, 0)
	for linhas.Next() {
		var resumo dominio.ResumoRecomendacao
		var custoTexto string
		if err := linhas.Scan(
			&resumo.ID, &resumo.ListaID, &resumo.GeradoEm, &custoTexto, &resumo.PesoConveniencia,
		); err != nil {
			return nil, fmt.Errorf("ler recomendação: %w", err)
		}
		if resumo.CustoTotalCentavos, err = dominio.ConverterReaisParaCentavos(
			custoTexto,
		); err != nil {
			return nil, fmt.Errorf("converter custo da recomendação: %w", err)
		}
		resumo.Perfil = dominio.PerfilDoPeso(resumo.PesoConveniencia)
		resumos = append(resumos, resumo)
	}
	return resumos, linhas.Err()
}

// BuscarRecomendacao devolve uma recomendação completa, com o payload bruto
// gravado no momento em que ela foi gerada.
func (r *Repositorio) BuscarRecomendacao(
	ctx context.Context, recomendacaoID int64,
) (RecomendacaoPersistida, error) {
	const consulta = `
		SELECT id, lista_id, gerado_em, parametro_peso_conveniencia::float8, payload_resultado
		  FROM recomendacoes
		 WHERE id = $1`

	var registro RecomendacaoPersistida
	var payload []byte
	err := r.pool.QueryRow(ctx, consulta, recomendacaoID).Scan(
		&registro.ID, &registro.ListaID, &registro.GeradoEm,
		&registro.PesoConveniencia, &payload,
	)
	if err != nil {
		return RecomendacaoPersistida{}, fmt.Errorf(
			"buscar recomendação: %w", traduzirErro(err, ""))
	}
	registro.Payload = payload
	return registro, nil
}
