package dominio

import "testing"

func TestPesoDoPerfil(t *testing.T) {
	casos := map[string]float64{
		PerfilEconomico:   0.0,
		PerfilEquilibrado: 1.0,
		PerfilConveniente: 3.0,
	}

	for perfil, esperado := range casos {
		obtido, err := PesoDoPerfil(perfil)
		if err != nil {
			t.Fatalf("PesoDoPerfil(%q) devolveu erro: %v", perfil, err)
		}
		if obtido != esperado {
			t.Errorf("PesoDoPerfil(%q) = %v; esperado %v", perfil, obtido, esperado)
		}
	}
}

func TestPesoDoPerfilRejeitaDesconhecido(t *testing.T) {
	for _, perfil := range []string{"", "barato", "ECONOMICO"} {
		if _, err := PesoDoPerfil(perfil); err == nil {
			t.Errorf("perfil %q deveria ser rejeitado", perfil)
		}
	}
}

// O caminho inverso é usado para rotular recomendações reabertas do histórico.
func TestPerfilDoPeso(t *testing.T) {
	if obtido := PerfilDoPeso(1.0); obtido != PerfilEquilibrado {
		t.Errorf("PerfilDoPeso(1.0) = %q; esperado %q", obtido, PerfilEquilibrado)
	}
	if obtido := PerfilDoPeso(0.0); obtido != PerfilEconomico {
		t.Errorf("PerfilDoPeso(0.0) = %q; esperado %q", obtido, PerfilEconomico)
	}
	// Peso livre dos experimentos da Fase 4 não corresponde a perfil nomeado.
	if obtido := PerfilDoPeso(1.7); obtido != "" {
		t.Errorf("PerfilDoPeso(1.7) = %q; esperado string vazia", obtido)
	}
}
