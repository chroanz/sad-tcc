# CLAUDE.md — Sistema de Apoio à Decisão para Compras de Supermercado (TCC)

Este arquivo orienta o Claude Code ao trabalhar neste repositório. Leia-o por completo antes de gerar ou alterar código.

## 1. Contexto do projeto

Prova de conceito de um Sistema de Apoio à Decisão (SAD) que recebe uma lista de compras
(produtos, marcas, quantidades, peso/volume) e recomenda **em quais supermercados comprar
cada item**, otimizando o trade-off entre:

- **Custo financeiro** (soma dos preços dos itens escolhidos nos mercados selecionados)
- **Conveniência** (nº de mercados a visitar). A distância percorrida não é precificada.

O usuário compra presencialmente — o sistema não faz e-commerce nem checkout. O resultado
final é uma recomendação: "vá a estes N mercados, nesta ordem, e compre estes itens em
cada um".

**Isto é uma PoC acadêmica de TCC, não um produto para produção.** Escopo geográfico e de
dados é deliberadamente pequeno (ver `plano_desenvolvimento.md`). Não adicione
funcionalidades fora do escopo (pagamento, delivery, multi-tenant, i18n, etc.) sem que o
autor peça explicitamente.

## 2. Arquitetura

```
┌─────────────────┐      HTTPS/JSON      ┌──────────────────┐
│  Frontend PWA    │ ───────────────────▶│  API Go (Gin)    │
│  (Svelte/Vue)    │◀─────────────────── │                  │
└─────────────────┘                      └───────┬──────────┘
                                                  │ HTTP interno (REST)
                                                  ▼
                                          ┌──────────────────┐
                                          │  Serviço Python   │
                                          │  (FastAPI +       │
                                          │   OR-Tools)       │
                                          └───────┬──────────┘
                                                  │
                                                  ▼
                                          ┌──────────────────┐
                                          │   PostgreSQL      │
                                          │ (+ PostGIS opc.)  │
                                          └──────────────────┘
```

- **API Go + Gin**: autenticação, CRUD (usuários, listas, produtos, marcas, mercados,
  preços/estoque), orquestração da chamada ao serviço de otimização, formatação da
  resposta final para o frontend. É o único serviço que fala com o Postgres.
- **Serviço Python (FastAPI + OR-Tools)**: stateless. Recebe via HTTP um payload já
  montado (lista de itens + candidatos de preço/disponibilidade por mercado + coordenadas)
  e devolve a alocação ótima + rota sugerida. Não acessa o banco diretamente — só recebe e
  devolve JSON. Isso mantém o serviço de otimização puro e fácil de testar isoladamente.
- **Postgres**: fonte única de verdade. Sem PostGIS: a distância em linha reta simples,
  calculada na aplicação, basta para a PoC (ela não é precificada).
- **Frontend PWA**: framework leve (Vue 3 + Vite + `vite-plugin-pwa`, ou SvelteKit).
  Prioridade: formulário de lista de compras rápido de preencher no celular, e uma tela de
  resultado clara (mercados, itens por mercado, economia estimada, mapa/rota opcional).

## 3. Stack e versões

- Go 1.22+, Gin
- Python 3.11+, FastAPI, Google OR-Tools (`ortools` — usar o solver **CP-SAT**, não o MIP
  solver antigo, salvo necessidade específica)
- PostgreSQL 15+
- Frontend: Vue 3 + Vite (ou SvelteKit, decisão do autor) + Workbox/vite-plugin-pwa

## 4. Modelo de dados (mínimo viável para a PoC)

- `usuarios` (id, nome, email, senha_hash)
- `produtos` (id, nome, categoria) — item genérico, ex. "arroz"
- `marcas` (id, produto_id, nome) — ex. "arroz Tio João"
- `mercados` (id, nome, latitude, longitude, endereco)
- `precos` (id, marca_id, mercado_id, preco, unidade, quantidade_disponivel, coletado_em)
  — na PoC, carregado da base do DIEESE (ver §5, "Dados")
  — snapshot de preço/disponibilidade; **nunca sobrescrever, sempre inserir novo registro**
  para manter histórico de séries (relevante para a fundamentação teórica do TCC).
- `listas_compra` (id, usuario_id, nome, criado_em)
- `itens_lista` (id, lista_id, produto_id, marca_id opcional, quantidade, unidade)
- `recomendacoes` (id, lista_id, gerado_em, custo_total, parametro_peso_conveniencia,
  payload_resultado jsonb) — guardar o resultado retornado pelo otimizador para
  auditoria/comparação nos testes de acurácia da Fase 4.

## 5. Regra de domínio central — função objetivo

O núcleo do sistema é um modelo de Programação Inteira Mista multiobjetivo:

- Variáveis binárias `x[i][j]` = item `i` comprado no mercado `j`. Criada **apenas para
  pares candidatos**: existe preço cadastrado e o estoque cobre a quantidade pedida. A
  restrição de estoque é aplicada na construção do conjunto de candidatos, não como
  desigualdade no modelo.
- Variáveis binárias `y[j]` = mercado `j` é visitado
- Variáveis binárias `u[i]` = item `i` fica **sem atendimento**, com penalidade alta. É ela
  que impede o modelo de ficar inviável quando algum item não tem oferta em mercado nenhum:
  o solver sempre devolve uma recomendação para os demais itens e reporta o que faltou.
- Restrições: atribuição exata `Σ_j x[i][j] + u[i] = 1` (a quantidade de um item nunca é
  dividida entre mercados); `x[i][j] <= y[j]` (só compra onde visita).
- Objetivo (escalarização por soma ponderada, parametrizável pelo usuário):

  `min  custo_total(x)  +  peso_conveniencia * custo_por_visita * Σ_j y[j]  +  M * Σ_i u[i]`

  **O SAD decide por preço e disponibilidade.** A distância percorrida **não é precificada**
  e não entra no objetivo (decisão do autor para simplificar a PoC). A conveniência é
  medida só pelo número de mercados visitados. Não há variáveis de arco, `AddCircuit` nem
  custo por km. As versões anteriores (ida e volta linearizada e, depois, circuito no
  CP-SAT) estão registradas em `modelo/docs/formulacao-matematica.md` §7.

  `M` não é um número grande arbitrário: é a maior economia concebível ao abandonar um item
  (soma de todos os custos candidatos mais o custo ponderado de visitar todos os mercados)
  somada a 1, o que garante que nenhuma solução deixe de atender um item atendível.

- **Ordem de visita, depois do solve** (`modelo/app/otimizacao/rota.py`): um único percurso.
  O usuário sai da origem uma vez, vai sempre ao mercado ainda não visitado mais próximo de
  onde está e volta para casa no fim (vizinho mais próximo). Nunca uma ida e volta por
  mercado. A distância, em linha reta (sem haversine), é só informativa.
- Perfis fixos de `peso_conveniencia`: `economico` = 0.0, `equilibrado` = 1.0,
  `conveniente` = 3.0. A API também aceita um peso numérico livre, para os experimentos da
  Fase 4.
- Aritmética **inteira**: dinheiro em centavos e distância em metros; o peso fracionário é
  escalado por 100. O CP-SAT não aceita coeficiente fracionário.
- **Dados e escopo**: o escopo geográfico é **Juazeiro do Norte/CE**. Os preços vêm da base
  da cesta básica do DIEESE (`cesta_agosto.csv`): cada nome de cidade do CSV vira um
  **supermercado fictício dentro de Juazeiro** ("Supermercado Fortaleza"...), com os preços
  DIEESE daquela cidade e localização fictícia num raio de 6 km do centro. Os itens se
  restringem aos da cesta e cada produto tem duas marcas fictícias (±8% do preço DIEESE). Célula `-` = indisponível. O catálogo é gerado
  por `dados/gerar_catalogo_dieese.py` (migration `004_catalogo_dieese.sql`). Não há coleta
  de preços em supermercados.
- **Desempate determinístico em duas fases**: com `peso_conveniencia = 0` existem várias
  soluções de custo idêntico. A fase 1 minimiza o objetivo e guarda `Z*`; a fase 2 fixa
  `objetivo == Z*` e minimiza, em ordem lexicográfica, o número de mercados e depois a
  soma das distâncias dos mercados à origem (a distância só desempata, nunca muda `Z*`).
  Sem isso a validação da Fase 4 acusaria falsas divergências.
- **Não implemente um branch-and-bound manual, nem um TSP.** Use
  `ortools.sat.python.cp_model` (CP-SAT). A contribuição do TCC está na formulação do
  modelo e na escolha dos pesos, não no algoritmo de busca do solver.
- Para o teste de acurácia (Fase 4 do TCC), instâncias pequenas devem ser validadas por
  enumeração exaustiva em um script Python separado (`modelo/scripts/validacao_exaustiva.py`),
  comparando o custo obtido por enumeração com o custo devolvido pelo CP-SAT. A enumeração
  precisa ser uma **implementação independente** — reaproveitar a aritmética do modelo
  invalidaria a comparação.

A formulação completa, com notação matemática e justificativas, está em
`modelo/docs/formulacao-matematica.md`.

## 6. Convenções de código

- Go: `gofmt`/`golangci-lint` limpos antes de qualquer commit; handlers do Gin finos,
  lógica de negócio em pacotes `internal/service`; erros sempre com contexto (`fmt.Errorf("%w")`).
- Python: `black` + `ruff`; validação de entrada/saída com Pydantic; toda função pública
  do serviço de otimização deve ter type hints e docstring explicando as variáveis do
  modelo (isso vira documentação direta para o capítulo de metodologia do TCC).
- Commits pequenos e descritivos em português ou inglês, mas consistente dentro do
  projeto — não misturar idioma no mesmo commit.
- Sempre que alterar a função objetivo ou as restrições do modelo de otimização, atualizar
  a seção 5 deste arquivo e o capítulo de metodologia correspondente no texto do TCC.

## 7. O que NÃO fazer sem confirmação explícita do autor

- Não adicionar autenticação social, multi-idioma, pagamento, ou infraestrutura de
  produção (Kubernetes, CI/CD complexo) — isso é uma PoC de TCC com prazo fixo.
- Não trocar OR-Tools por outra biblioteca de otimização sem discutir o impacto no
  texto do TCC (ver seção 5).
- Não aumentar o escopo geográfico/de dados definido em `plano_desenvolvimento.md` sem
  atualizar também o cronograma.

## 8. Comandos úteis (preencher conforme o setup real do repositório)

```bash
# Tudo de uma vez
docker compose up --build

# --- ou serviço a serviço ---

# Banco
docker compose up -d postgres

# Serviço Python de otimização (porta 8001)
cd modelo && uvicorn app.main:app --reload --port 8001

# API Go (porta 8080; aplica as migrations na subida)
cd api && go run ./cmd/servidor

# PWA (porta 5173)
cd pwa && npm run dev
```

Portões de qualidade:

```bash
cd modelo && pytest testes -q && black --line-length 100 --check . && ruff check .
cd modelo && python scripts/validacao_exaustiva.py --repeticoes 60
cd api && gofmt -l . && go vet ./... && go test ./...
cd pwa && npm run build
```

Os diretórios são `api/`, `modelo/` e `pwa/` (não `optimizer/` nem `frontend/`).
Documentação completa em `docs/README.md`.
