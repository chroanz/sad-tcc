package dominio

import (
	"errors"
	"fmt"
)

// Erros sentinela do domínio. A camada de transporte é a única que os traduz
// para códigos HTTP; serviços e repositórios apenas os embrulham com contexto.
var (
	// ErrNaoEncontrado indica recurso inexistente (HTTP 404).
	ErrNaoEncontrado = errors.New("recurso não encontrado")
	// ErrNaoAutenticado indica token ausente, inválido ou expirado (HTTP 401).
	ErrNaoAutenticado = errors.New("não autenticado")
	// ErrNaoAutorizado indica recurso pertencente a outro usuário (HTTP 403).
	ErrNaoAutorizado = errors.New("acesso não autorizado ao recurso")
	// ErrConflito indica violação de unicidade (HTTP 409).
	ErrConflito = errors.New("conflito com registro existente")
	// ErrOtimizadorIndisponivel indica falha de comunicação com o serviço
	// Python de otimização (HTTP 503).
	ErrOtimizadorIndisponivel = errors.New("serviço de otimização indisponível")
)

// ErroValidacao representa uma regra de entrada violada (HTTP 400). Carrega a
// mensagem exibida ao cliente, por isso não deve conter detalhes internos.
type ErroValidacao struct {
	Mensagem string
}

func (e *ErroValidacao) Error() string {
	return e.Mensagem
}

// NovoErroValidacao cria um ErroValidacao com mensagem formatada.
func NovoErroValidacao(formato string, argumentos ...any) error {
	return &ErroValidacao{Mensagem: fmt.Sprintf(formato, argumentos...)}
}

// ErroConflito permite anexar uma mensagem específica a um conflito de
// unicidade mantendo a correspondência com ErrConflito via errors.Is.
type ErroConflito struct {
	Mensagem string
}

func (e *ErroConflito) Error() string {
	return e.Mensagem
}

// Unwrap liga ErroConflito ao sentinela ErrConflito.
func (e *ErroConflito) Unwrap() error {
	return ErrConflito
}

// NovoErroConflito cria um ErroConflito com mensagem formatada.
func NovoErroConflito(formato string, argumentos ...any) error {
	return &ErroConflito{Mensagem: fmt.Sprintf(formato, argumentos...)}
}
