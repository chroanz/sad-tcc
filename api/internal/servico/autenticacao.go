// Package servico concentra a regra de negócio. Handlers HTTP apenas traduzem
// entrada e saída; nada de lógica de domínio vive na camada de transporte.
package servico

import (
	"context"
	"errors"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"golang.org/x/crypto/bcrypt"

	"github.com/tcc/sad-compras/api/internal/dominio"
	"github.com/tcc/sad-compras/api/internal/repositorio"
)

// tamanhoMinimoSenha espelha o contrato REST: senha com ao menos 8 caracteres.
const tamanhoMinimoSenha = 8

// Autenticacao cuida de cadastro, login e emissão/validação de tokens.
type Autenticacao struct {
	repositorio *repositorio.Repositorio
	segredo     []byte
	validade    time.Duration
}

// SessaoAberta é o que o cliente recebe ao se cadastrar ou entrar.
type SessaoAberta struct {
	Token   string          `json:"token"`
	Usuario dominio.Usuario `json:"usuario"`
}

// NovaAutenticacao monta o serviço com o segredo e a validade do JWT.
func NovaAutenticacao(
	repo *repositorio.Repositorio, segredo string, validade time.Duration,
) *Autenticacao {
	return &Autenticacao{repositorio: repo, segredo: []byte(segredo), validade: validade}
}

// Registrar cria o usuário com a senha protegida por bcrypt e já devolve uma
// sessão aberta, para o cliente não precisar fazer login em seguida.
func (a *Autenticacao) Registrar(
	ctx context.Context, nome, email, senha string,
) (SessaoAberta, error) {
	nome = strings.TrimSpace(nome)
	email = strings.ToLower(strings.TrimSpace(email))

	if nome == "" {
		return SessaoAberta{}, dominio.NovoErroValidacao("nome é obrigatório")
	}
	if !strings.Contains(email, "@") {
		return SessaoAberta{}, dominio.NovoErroValidacao("e-mail inválido")
	}
	if len(senha) < tamanhoMinimoSenha {
		return SessaoAberta{}, dominio.NovoErroValidacao(
			"a senha deve ter ao menos %d caracteres", tamanhoMinimoSenha)
	}

	hash, err := bcrypt.GenerateFromPassword([]byte(senha), bcrypt.DefaultCost)
	if err != nil {
		return SessaoAberta{}, fmt.Errorf("gerar hash da senha: %w", err)
	}

	usuario, err := a.repositorio.CriarUsuario(ctx, nome, email, string(hash))
	if err != nil {
		return SessaoAberta{}, err
	}
	return a.abrirSessao(usuario)
}

// Entrar confere as credenciais. A mensagem de erro é a mesma para e-mail
// inexistente e senha errada, para não revelar quais e-mails estão cadastrados.
func (a *Autenticacao) Entrar(
	ctx context.Context, email, senha string,
) (SessaoAberta, error) {
	email = strings.ToLower(strings.TrimSpace(email))

	usuario, err := a.repositorio.BuscarUsuarioPorEmail(ctx, email)
	if err != nil {
		if errors.Is(err, dominio.ErrNaoEncontrado) {
			return SessaoAberta{}, dominio.ErrNaoAutenticado
		}
		return SessaoAberta{}, err
	}

	if bcrypt.CompareHashAndPassword([]byte(usuario.SenhaHash), []byte(senha)) != nil {
		return SessaoAberta{}, dominio.ErrNaoAutenticado
	}
	return a.abrirSessao(usuario)
}

// abrirSessao emite o JWT HS256 com o id do usuário no subject.
func (a *Autenticacao) abrirSessao(usuario dominio.Usuario) (SessaoAberta, error) {
	agora := time.Now()
	afirmacoes := jwt.RegisteredClaims{
		Subject:   strconv.FormatInt(usuario.ID, 10),
		IssuedAt:  jwt.NewNumericDate(agora),
		ExpiresAt: jwt.NewNumericDate(agora.Add(a.validade)),
	}

	token, err := jwt.NewWithClaims(jwt.SigningMethodHS256, afirmacoes).SignedString(a.segredo)
	if err != nil {
		return SessaoAberta{}, fmt.Errorf("assinar token: %w", err)
	}
	return SessaoAberta{Token: token, Usuario: usuario}, nil
}

// ValidarToken confere a assinatura e a validade do token e devolve o id do
// usuário. Qualquer falha vira ErrNaoAutenticado: o cliente não precisa saber
// se o token estava expirado ou malformado.
func (a *Autenticacao) ValidarToken(token string) (int64, error) {
	analisado, err := jwt.ParseWithClaims(
		token,
		&jwt.RegisteredClaims{},
		func(t *jwt.Token) (any, error) {
			if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, fmt.Errorf("método de assinatura inesperado: %v", t.Header["alg"])
			}
			return a.segredo, nil
		},
		jwt.WithValidMethods([]string{jwt.SigningMethodHS256.Alg()}),
	)
	if err != nil || !analisado.Valid {
		return 0, dominio.ErrNaoAutenticado
	}

	afirmacoes, ok := analisado.Claims.(*jwt.RegisteredClaims)
	if !ok {
		return 0, dominio.ErrNaoAutenticado
	}

	usuarioID, err := strconv.ParseInt(afirmacoes.Subject, 10, 64)
	if err != nil {
		return 0, dominio.ErrNaoAutenticado
	}
	return usuarioID, nil
}
