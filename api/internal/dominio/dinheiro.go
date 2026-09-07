package dominio

import (
	"strconv"
	"strings"
)

// ConverterReaisParaCentavos converte um valor monetário decimal, recebido como
// texto (a forma em que NUMERIC(10,2) sai do PostgreSQL e em que json.Number
// preserva o literal enviado pelo cliente), para centavos inteiros.
//
// O valor nunca passa por float64: a conversão é feita sobre os dígitos, de
// modo que 25.99 vira exatamente 2599. Quando há mais de duas casas decimais o
// arredondamento é explícito, meio-para-cima afastando-se do zero
// (0.005 -> 1 centavo, -0.005 -> -1 centavo).
func ConverterReaisParaCentavos(reais string) (int64, error) {
	texto := strings.TrimSpace(reais)
	if texto == "" {
		return 0, NovoErroValidacao("valor monetário vazio")
	}

	negativo := false
	switch texto[0] {
	case '+':
		texto = texto[1:]
	case '-':
		negativo = true
		texto = texto[1:]
	}

	inteira, fracionaria, encontrouPonto := strings.Cut(texto, ".")
	if inteira == "" && fracionaria == "" {
		return 0, NovoErroValidacao("valor monetário inválido: %q", reais)
	}
	if inteira == "" {
		inteira = "0"
	}
	if encontrouPonto && fracionaria == "" {
		return 0, NovoErroValidacao("valor monetário inválido: %q", reais)
	}
	if !apenasDigitos(inteira) || !apenasDigitos(fracionaria) {
		return 0, NovoErroValidacao("valor monetário inválido: %q", reais)
	}

	parteInteira, err := strconv.ParseInt(inteira, 10, 64)
	if err != nil {
		return 0, NovoErroValidacao("valor monetário fora da faixa suportada: %q", reais)
	}

	// Normaliza a parte fracionária para exatamente duas casas, guardando o
	// terceiro dígito para decidir o arredondamento.
	fracionariaPreenchida := fracionaria + "000"
	centavosFracao, err := strconv.ParseInt(fracionariaPreenchida[:2], 10, 64)
	if err != nil {
		return 0, NovoErroValidacao("valor monetário inválido: %q", reais)
	}
	terceiroDigito := fracionariaPreenchida[2] - '0'

	centavos := parteInteira*100 + centavosFracao
	if terceiroDigito >= 5 {
		centavos++
	}
	if negativo {
		centavos = -centavos
	}
	return centavos, nil
}

// ConverterCentavosParaReais devolve a representação decimal com duas casas de
// um valor em centavos, no formato aceito por NUMERIC(10,2). A conversão é
// exata e não usa ponto flutuante.
func ConverterCentavosParaReais(centavos int64) string {
	sinal := ""
	if centavos < 0 {
		sinal = "-"
		centavos = -centavos
	}
	return sinal + strconv.FormatInt(centavos/100, 10) + "." +
		leftPad(strconv.FormatInt(centavos%100, 10), 2)
}

func apenasDigitos(texto string) bool {
	for i := 0; i < len(texto); i++ {
		if texto[i] < '0' || texto[i] > '9' {
			return false
		}
	}
	return true
}

func leftPad(texto string, tamanho int) string {
	for len(texto) < tamanho {
		texto = "0" + texto
	}
	return texto
}

// ConverterTextoParaQuantidade interpreta um NUMERIC(12,3) vindo do banco (ou
// um json.Number do cliente) como float64. Quantidades, ao contrário de
// dinheiro, são float por definição do contrato de otimização.
func ConverterTextoParaQuantidade(texto string) (float64, error) {
	valor, err := strconv.ParseFloat(strings.TrimSpace(texto), 64)
	if err != nil {
		return 0, NovoErroValidacao("quantidade inválida: %q", texto)
	}
	return valor, nil
}
