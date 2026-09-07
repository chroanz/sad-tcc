package repositorio

import (
	"context"
	"fmt"

	"github.com/tcc/sad-compras/api/internal/dominio"
)

// CriarUsuario insere um novo usuário. O e-mail é único no esquema; a violação
// vira ErrConflito.
func (r *Repositorio) CriarUsuario(
	ctx context.Context, nome, email, senhaHash string,
) (dominio.Usuario, error) {
	const consulta = `
		INSERT INTO usuarios (nome, email, senha_hash)
		VALUES ($1, $2, $3)
		RETURNING id, nome, email, senha_hash, criado_em`

	var usuario dominio.Usuario
	err := r.pool.QueryRow(ctx, consulta, nome, email, senhaHash).Scan(
		&usuario.ID, &usuario.Nome, &usuario.Email, &usuario.SenhaHash, &usuario.CriadoEm,
	)
	if err != nil {
		return dominio.Usuario{}, fmt.Errorf(
			"criar usuário: %w", traduzirErro(err, "e-mail já cadastrado"))
	}
	return usuario, nil
}

// BuscarUsuarioPorEmail devolve o usuário com o hash da senha, para conferência
// no login.
func (r *Repositorio) BuscarUsuarioPorEmail(
	ctx context.Context, email string,
) (dominio.Usuario, error) {
	const consulta = `
		SELECT id, nome, email, senha_hash, criado_em
		  FROM usuarios
		 WHERE email = $1`

	var usuario dominio.Usuario
	err := r.pool.QueryRow(ctx, consulta, email).Scan(
		&usuario.ID, &usuario.Nome, &usuario.Email, &usuario.SenhaHash, &usuario.CriadoEm,
	)
	if err != nil {
		return dominio.Usuario{}, fmt.Errorf("buscar usuário por e-mail: %w", traduzirErro(err, ""))
	}
	return usuario, nil
}

// BuscarUsuarioPorID é usado pelo middleware para confirmar que o usuário do
// token ainda existe.
func (r *Repositorio) BuscarUsuarioPorID(
	ctx context.Context, id int64,
) (dominio.Usuario, error) {
	const consulta = `
		SELECT id, nome, email, senha_hash, criado_em
		  FROM usuarios
		 WHERE id = $1`

	var usuario dominio.Usuario
	err := r.pool.QueryRow(ctx, consulta, id).Scan(
		&usuario.ID, &usuario.Nome, &usuario.Email, &usuario.SenhaHash, &usuario.CriadoEm,
	)
	if err != nil {
		return dominio.Usuario{}, fmt.Errorf("buscar usuário por id: %w", traduzirErro(err, ""))
	}
	return usuario, nil
}
