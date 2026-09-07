package transporte

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"

	"github.com/tcc/sad-compras/api/internal/dominio"
)

// A tradução erro de domínio -> HTTP acontece num único lugar; este teste é o
// que garante que o contrato REST e o código não se separem.
func TestResponderErroMapeiaOContratoRest(t *testing.T) {
	gin.SetMode(gin.TestMode)

	casos := []struct {
		nome           string
		erro           error
		statusEsperado int
		codigoEsperado string
	}{
		{
			"validação",
			dominio.NovoErroValidacao("quantidade deve ser maior que zero"),
			http.StatusBadRequest, CodigoValidacao,
		},
		{"não autenticado", dominio.ErrNaoAutenticado, http.StatusUnauthorized, CodigoNaoAutenticado},
		{"não autorizado", dominio.ErrNaoAutorizado, http.StatusForbidden, CodigoNaoAutorizado},
		{"não encontrado", dominio.ErrNaoEncontrado, http.StatusNotFound, CodigoNaoEncontrado},
		{"conflito", dominio.NovoErroConflito("e-mail já cadastrado"), http.StatusConflict, CodigoConflito},
		{
			"otimizador fora do ar",
			dominio.ErrOtimizadorIndisponivel,
			http.StatusServiceUnavailable, CodigoOtimizadorIndisponivel,
		},
		{"inesperado", errors.New("falha de disco"), http.StatusInternalServerError, CodigoErroInterno},
	}

	for _, caso := range casos {
		t.Run(caso.nome, func(t *testing.T) {
			gravador := httptest.NewRecorder()
			contexto, _ := gin.CreateTestContext(gravador)

			responderErro(contexto, caso.erro)

			if gravador.Code != caso.statusEsperado {
				t.Errorf("status = %d; esperado %d", gravador.Code, caso.statusEsperado)
			}

			var corpo corpoErro
			if err := json.Unmarshal(gravador.Body.Bytes(), &corpo); err != nil {
				t.Fatalf("resposta não é o envelope de erro: %v", err)
			}
			if corpo.Erro.Codigo != caso.codigoEsperado {
				t.Errorf("código = %q; esperado %q", corpo.Erro.Codigo, caso.codigoEsperado)
			}
			if corpo.Erro.Mensagem == "" {
				t.Error("mensagem de erro não pode ser vazia")
			}
		})
	}
}

// O erro precisa continuar sendo reconhecido depois de embrulhado com contexto
// pelas camadas de serviço e repositório.
func TestErroEmbrulhadoPreservaOMapeamento(t *testing.T) {
	gin.SetMode(gin.TestMode)

	gravador := httptest.NewRecorder()
	contexto, _ := gin.CreateTestContext(gravador)

	embrulhado := fmt.Errorf("buscar lista: %w", dominio.ErrNaoEncontrado)
	responderErro(contexto, embrulhado)

	if gravador.Code != http.StatusNotFound {
		t.Errorf("status = %d; esperado 404", gravador.Code)
	}
}

// Detalhes internos nunca podem vazar na resposta de erro 500.
func TestErroInternoNaoVazaMensagemOriginal(t *testing.T) {
	gin.SetMode(gin.TestMode)

	gravador := httptest.NewRecorder()
	contexto, _ := gin.CreateTestContext(gravador)

	responderErro(contexto, errors.New("connection refused em 10.0.0.5:5432"))

	if bytes := gravador.Body.String(); contemSegredo(bytes) {
		t.Errorf("a resposta vazou detalhe interno: %s", bytes)
	}
}

func contemSegredo(corpo string) bool {
	for _, trecho := range []string{"10.0.0.5", "connection refused", "5432"} {
		if strings.Contains(corpo, trecho) {
			return true
		}
	}
	return false
}
