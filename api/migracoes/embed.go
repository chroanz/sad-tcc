// Package migracoes embute os arquivos SQL de migração do esquema.
//
// O arquivo vive dentro do diretório `migracoes/` porque a diretiva //go:embed
// só enxerga o próprio diretório do arquivo Go e seus subdiretórios. O runner
// que interpreta esses arquivos está em internal/banco/migracoes.go.
package migracoes

import "embed"

// Arquivos contém todos os scripts .sql do diretório, aplicados em ordem
// alfabética pelo runner de migrations.
//
//go:embed *.sql
var Arquivos embed.FS
