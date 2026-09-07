package dominio

// Perfis de recomendação previstos no contrato REST. Cada um corresponde a um
// valor fixo de peso_conveniencia na escalarização
// min custo_total(x) + peso_conveniencia * custo_logistico(y).
const (
	PerfilEconomico   = "economico"
	PerfilEquilibrado = "equilibrado"
	PerfilConveniente = "conveniente"
)

// pesosPorPerfil é a tabela de tradução perfil -> peso da seção "Recomendação"
// do contrato REST.
var pesosPorPerfil = map[string]float64{
	PerfilEconomico:   0.0,
	PerfilEquilibrado: 1.0,
	PerfilConveniente: 3.0,
}

// PesoDoPerfil traduz o nome do perfil no peso da parcela logística.
// Um perfil desconhecido é erro de validação.
func PesoDoPerfil(perfil string) (float64, error) {
	peso, existe := pesosPorPerfil[perfil]
	if !existe {
		return 0, NovoErroValidacao(
			"perfil inválido: %q; use economico, equilibrado ou conveniente", perfil)
	}
	return peso, nil
}

// PerfilDoPeso faz o caminho inverso, usado para reconstruir uma recomendação
// persistida. Devolve string vazia quando o peso não corresponde a nenhum
// perfil nomeado (caso dos experimentos da Fase 4 com peso livre).
func PerfilDoPeso(peso float64) string {
	for perfil, valor := range pesosPorPerfil {
		if valor == peso {
			return perfil
		}
	}
	return ""
}
