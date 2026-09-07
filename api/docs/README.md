# API Go (`api/`)

API REST que orquestra o sistema: autenticação, CRUD de catálogo e listas, chamada ao
serviço de otimização e persistência das recomendações. É o **único serviço que fala com o
PostgreSQL**.

## Documentação

| Documento | Conteúdo |
|---|---|
| [`arquitetura-interna.md`](arquitetura-interna.md) | camadas, regra de dependência, tratamento de erros, aritmética monetária |
| [`fluxo-recomendacao.md`](fluxo-recomendacao.md) | o caminho completo de uma recomendação, passo a passo |
| [`autenticacao.md`](autenticacao.md) | cadastro, login, JWT, escopo por usuário |
| [`migracoes.md`](migracoes.md) | runner de migrations e o append-only de `precos` |
| [`endpoints.md`](endpoints.md) | referência das rotas com exemplos de `curl` |
| [`../../docs/contrato-api-rest.md`](../../docs/contrato-api-rest.md) | o contrato com o PWA |

## Estrutura

```
api/
├── cmd/servidor/main.go        # composição, ciclo de vida, encerramento gracioso
├── internal/
│   ├── configuracao/           # variáveis de ambiente
│   ├── banco/                  # pool pgx e runner de migrations
│   ├── dominio/                # tipos, erros sentinela, dinheiro, perfis
│   ├── repositorio/            # SQL por agregado
│   ├── servico/                # regra de negócio
│   ├── otimizador/             # cliente HTTP do serviço Python
│   └── transporte/             # rotas Gin, handlers, middlewares
├── migracoes/                  # SQL embutido no binário
└── docs/
```

## Como rodar

Com o banco e o otimizador de pé:

```bash
cd api
go run ./cmd/servidor
```

A API aplica as migrations sozinha na subida quando `APLICAR_MIGRACOES=true`. Sem o
serviço Python no ar, o CRUD continua funcionando e apenas a rota de recomendação responde
`503 OTIMIZADOR_INDISPONIVEL`.

Em Docker: `docker compose up` sobe tudo na ordem correta.

## Como testar

```bash
gofmt -l .        # não pode listar nenhum arquivo
go vet ./...
go build ./...
go test ./...
```

Os testes não exigem banco: cobrem a conversão monetária, a tradução perfil para peso, o
mapeamento de erro de domínio para HTTP e a montagem do payload de otimização.

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `API_PORTA` | `8080` | porta HTTP |
| `BANCO_URL` | **sem padrão** | DSN do PostgreSQL; ausência é erro fatal |
| `JWT_SEGREDO` | **sem padrão** | chave HS256; ausência é erro fatal |
| `JWT_HORAS_VALIDADE` | `24` | validade do token |
| `OTIMIZADOR_URL` | `http://localhost:8001` | base do serviço Python |
| `OTIMIZADOR_TIMEOUT_SEGUNDOS` | `30` | teto da chamada ao otimizador |
| `APLICAR_MIGRACOES` | `true` | aplica as migrations na subida |
| `ORIGEM_PADRAO_LATITUDE` | `-7.213100` | centro de Juazeiro do Norte |
| `ORIGEM_PADRAO_LONGITUDE` | `-39.315300` | centro de Juazeiro do Norte |

## Requisitos de versão

`go.mod` declara **Go 1.24**. As dependências estão fixadas em versões compatíveis com
esse piso (`pgx v5.7.5`, `gin v1.10.1`, `jwt/v5 v5.2.1`), para que o repositório compile
sem exigir download automático de um toolchain mais novo.

## Convenções

- Identificadores, comentários e mensagens em **português brasileiro**.
- Handlers finos; regra de negócio em `internal/servico`.
- Erros sempre embrulhados com contexto (`fmt.Errorf("...: %w", err)`), traduzidos para
  HTTP num único ponto.
- Dinheiro em **centavos inteiros**; `float64` nunca toca em valor monetário.
- Sem ORM: `pgx` e SQL escrito à mão.
