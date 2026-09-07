# Referência de endpoints

Exemplos executáveis contra a API local. O contrato completo, com todos os campos, está em
[`../../docs/contrato-api-rest.md`](../../docs/contrato-api-rest.md).

Base: `http://localhost:8080/api/v1`

## Saúde

```bash
curl http://localhost:8080/saude
```

```json
{ "status": "ok", "banco": "ok", "otimizador": "ok" }
```

Responde `503` quando alguma dependência está fora do ar, com o campo correspondente
marcado como `indisponivel`.

## Autenticação

```bash
# Cadastro
curl -X POST http://localhost:8080/api/v1/auth/registrar \
  -H "Content-Type: application/json" \
  -d '{"nome":"Maria Silva","email":"maria@exemplo.com","senha":"segredo123"}'

# Login com o usuário de demonstração da semente
curl -X POST http://localhost:8080/api/v1/auth/entrar \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@exemplo.com","senha":"demo1234"}'
```

Guarde o token devolvido na variável `TOKEN` para os comandos seguintes.

## Catálogo

```bash
# Produtos, com filtro opcional por nome
curl "http://localhost:8080/api/v1/produtos?busca=arroz" -H "Authorization: Bearer $TOKEN"

curl -X POST http://localhost:8080/api/v1/produtos \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nome":"Arroz","categoria":"Mercearia"}'

# Marcas de um produto
curl http://localhost:8080/api/v1/produtos/1/marcas -H "Authorization: Bearer $TOKEN"

curl -X POST http://localhost:8080/api/v1/marcas \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"produto_id":1,"nome":"Tio Joao 5kg"}'

# Mercados
curl http://localhost:8080/api/v1/mercados -H "Authorization: Bearer $TOKEN"

curl -X POST http://localhost:8080/api/v1/mercados \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nome":"Mercado Novo","latitude":-7.2208,"longitude":-39.3042,"endereco":"Av. Ailton Gomes, 980 - Salesianos"}'
```

## Preços

```bash
# Preços vigentes de um mercado (leitura da view precos_vigentes)
curl "http://localhost:8080/api/v1/precos?mercado_id=1&vigentes=true" \
  -H "Authorization: Bearer $TOKEN"

# Histórico completo de uma marca (série append-only)
curl "http://localhost:8080/api/v1/precos?marca_id=7" -H "Authorization: Bearer $TOKEN"

# Nova coleta: sempre INSERT, nunca UPDATE
curl -X POST http://localhost:8080/api/v1/precos \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"marca_id":7,"mercado_id":1,"preco":"25.99","unidade":"un","quantidade_disponivel":12}'
```

O campo `preco` vai como **string decimal**, para não passar por ponto flutuante no JSON.
`coletado_em` é opcional e assume o instante atual.

## Listas e itens

```bash
curl http://localhost:8080/api/v1/listas -H "Authorization: Bearer $TOKEN"

curl -X POST http://localhost:8080/api/v1/listas \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"nome":"Compras do mes"}'

# Lista com os itens expandidos
curl http://localhost:8080/api/v1/listas/1 -H "Authorization: Bearer $TOKEN"

# Item com marca fixa
curl -X POST http://localhost:8080/api/v1/listas/1/itens \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"produto_id":1,"marca_id":7,"quantidade":2,"unidade":"un"}'

# Item com marca livre: qualquer marca do produto serve, e costuma render mais economia
curl -X POST http://localhost:8080/api/v1/listas/1/itens \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"produto_id":2,"marca_id":null,"quantidade":1,"unidade":"un"}'

curl -X DELETE http://localhost:8080/api/v1/listas/1/itens/5 -H "Authorization: Bearer $TOKEN"
```

Unidades aceitas: `kg`, `g`, `L`, `ml`, `un`.

## Recomendação

```bash
# Um perfil por vez, na mesma lista, para comparar o trade-off
curl -X POST http://localhost:8080/api/v1/listas/1/recomendacoes \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"perfil":"economico"}'

curl -X POST http://localhost:8080/api/v1/listas/1/recomendacoes \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"perfil":"equilibrado"}'

curl -X POST http://localhost:8080/api/v1/listas/1/recomendacoes \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"perfil":"conveniente"}'
```

Espera-se que `economico` visite mais mercados e gaste menos em itens, e que `conveniente`
faça o oposto. Essa comparação é o experimento central da Fase 4.

```bash
# Peso livre, para varrer a fronteira de Pareto
curl -X POST http://localhost:8080/api/v1/listas/1/recomendacoes \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"peso_conveniencia":0.5}'

# Origem explícita; sem ela a resposta traz origem_aproximada: true
curl -X POST http://localhost:8080/api/v1/listas/1/recomendacoes \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"perfil":"equilibrado","origem":{"latitude":-7.2131,"longitude":-39.3153}}'

# Histórico e reabertura (esta última nunca recalcula)
curl http://localhost:8080/api/v1/listas/1/recomendacoes -H "Authorization: Bearer $TOKEN"
curl http://localhost:8080/api/v1/recomendacoes/15 -H "Authorization: Bearer $TOKEN"
```

## Erros

Todos seguem o mesmo envelope:

```json
{ "erro": { "codigo": "VALIDACAO", "mensagem": "quantidade deve ser maior que zero", "detalhes": null } }
```

| Código | HTTP | Como provocar |
|---|---|---|
| `VALIDACAO` | 400 | quantidade zero, unidade fora da lista, lista acima de 20 itens |
| `NAO_AUTENTICADO` | 401 | omitir o cabeçalho `Authorization` |
| `NAO_AUTORIZADO` | 403 | acessar lista de outro usuário |
| `NAO_ENCONTRADO` | 404 | id inexistente |
| `CONFLITO` | 409 | cadastrar o mesmo e-mail duas vezes |
| `OTIMIZADOR_INDISPONIVEL` | 503 | derrubar o serviço Python e pedir recomendação |
| `ERRO_INTERNO` | 500 | falha inesperada; a mensagem original fica só no log |
