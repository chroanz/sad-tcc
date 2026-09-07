package dominio

import "testing"

func TestConverterReaisParaCentavos(t *testing.T) {
	casos := []struct {
		entrada  string
		esperado int64
	}{
		{"25.99", 2599},
		{"0.01", 1},
		{"0.10", 10},
		{"1", 100},
		{"1.", 0}, // inválido, tratado no teste de erro
		{"100.00", 10000},
		{"7.5", 750},
		{"1234.56", 123456},
		{"-3.20", -320},
		{"+4.05", 405},
		{" 8.99 ", 899},
	}

	for _, caso := range casos {
		if caso.entrada == "1." {
			continue
		}
		obtido, err := ConverterReaisParaCentavos(caso.entrada)
		if err != nil {
			t.Fatalf("ConverterReaisParaCentavos(%q) devolveu erro: %v", caso.entrada, err)
		}
		if obtido != caso.esperado {
			t.Errorf("ConverterReaisParaCentavos(%q) = %d; esperado %d",
				caso.entrada, obtido, caso.esperado)
		}
	}
}

// O arredondamento da terceira casa é explícito e afasta-se do zero, para que
// o valor não dependa da paridade como no arredondamento bancário.
func TestConverterReaisArredondaTerceiraCasa(t *testing.T) {
	casos := map[string]int64{
		"1.005": 101,
		"1.004": 100,
		"2.999": 300,
		"0.005": 1,
	}

	for entrada, esperado := range casos {
		obtido, err := ConverterReaisParaCentavos(entrada)
		if err != nil {
			t.Fatalf("erro inesperado em %q: %v", entrada, err)
		}
		if obtido != esperado {
			t.Errorf("ConverterReaisParaCentavos(%q) = %d; esperado %d", entrada, obtido, esperado)
		}
	}
}

func TestConverterReaisRejeitaEntradaInvalida(t *testing.T) {
	invalidos := []string{"", "abc", "1.", "1.2.3", "R$ 10,00", "10,50"}

	for _, entrada := range invalidos {
		if _, err := ConverterReaisParaCentavos(entrada); err == nil {
			t.Errorf("ConverterReaisParaCentavos(%q) deveria falhar", entrada)
		}
	}
}

func TestConverterCentavosParaReais(t *testing.T) {
	casos := map[int64]string{
		2599:   "25.99",
		1:      "0.01",
		100:    "1.00",
		0:      "0.00",
		-320:   "-3.20",
		123456: "1234.56",
	}

	for entrada, esperado := range casos {
		if obtido := ConverterCentavosParaReais(entrada); obtido != esperado {
			t.Errorf("ConverterCentavosParaReais(%d) = %q; esperado %q",
				entrada, obtido, esperado)
		}
	}
}

// A ida e volta entre as duas conversões precisa ser exata: é ela que garante
// que o valor gravado no banco e o valor enviado ao otimizador são o mesmo.
func TestConversaoMonetariaEhReversivel(t *testing.T) {
	for _, centavos := range []int64{0, 1, 99, 100, 2599, 999999} {
		texto := ConverterCentavosParaReais(centavos)
		obtido, err := ConverterReaisParaCentavos(texto)
		if err != nil {
			t.Fatalf("erro ao reconverter %q: %v", texto, err)
		}
		if obtido != centavos {
			t.Errorf("ida e volta de %d resultou em %d (texto %q)", centavos, obtido, texto)
		}
	}
}

func TestValidarUnidade(t *testing.T) {
	for _, unidade := range UnidadesValidas {
		if err := ValidarUnidade(unidade); err != nil {
			t.Errorf("unidade %q deveria ser válida: %v", unidade, err)
		}
	}
	for _, unidade := range []string{"", "KG", "litro", "un ", "dz"} {
		if err := ValidarUnidade(unidade); err == nil {
			t.Errorf("unidade %q deveria ser rejeitada", unidade)
		}
	}
}
