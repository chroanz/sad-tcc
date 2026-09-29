# Plano de Desenvolvimento — TCC II (2026.2)

Este plano traduz o cronograma do TCC 1 (jul–dez/2026) em tarefas técnicas concretas,
usando a stack Go+Gin / Python+OR-Tools / Postgres / PWA. Use junto com o `CLAUDE.md`.

## Decisão de escopo (definir ANTES de codar, e registrar no texto do TCC)

Estes números estão **travados** e vão para o texto do TCC 2 e para os testes de validação.

> **Revisão de escopo (2026-09-28).** Para simplificar a PoC, o autor substituiu a coleta
> manual em supermercados pela base pública do DIEESE e tirou o custo da distância do
> modelo. O escopo anterior (6 supermercados de Juazeiro do Norte, 18 produtos, coleta
> semanal) foi abandonado.

- Fonte de preços: **Pesquisa Nacional da Cesta Básica do DIEESE, agosto de 2026**
  (`cesta_agosto.csv`, na raiz do projeto). **Não há coleta** em supermercados.
- Recorte geográfico: **Juazeiro do Norte / CE**, raio de ~7 km do centro.
- Supermercados: **28 supermercados fictícios em Juazeiro do Norte**, um para cada nome de
  cidade do CSV ("Supermercado Fortaleza", "Supermercado Recife"...). Cada um pratica os
  preços DIEESE da cidade que lhe dá nome e tem localização fictícia num raio de 6 km do
  centro. O "Supermercado Macaé" existe, mas não oferta nada (Macaé não tem preços no CSV).
- Itens: os **13 produtos** da cesta, e só eles, com **2 marcas fictícias por produto**
  (±8% do preço DIEESE).
- Disponibilidade: célula `-` no CSV = produto indisponível naquela cidade.
- Decisão por **preço e disponibilidade**; a distância percorrida **não é precificada**.
- Origem padrão: centro de Juazeiro do Norte/CE (latitude -7,2131 / longitude -39,3153).

Dimensionamento derivado: instância típica de **13 itens × 28 mercados** (o raio padrão de
7 km alcança todos); teto suportado pela PoC de **20 itens × 30 mercados**.

> O catálogo é gerado por `dados/gerar_catalogo_dieese.py` e carregado pela migration
> `api/migracoes/004_catalogo_dieese.sql`, que remove a base fictícia de
> `002_dados_semente.sql`.

## Fase 1 — Análise de Sistemas e Requisitos (Julho)

- [ ] Levantar requisitos funcionais (cadastro de lista, cadastro de mercado/preço,
      geração de recomendação, visualização de economia) e não funcionais (tempo de
      resposta do otimizador, nº máximo de itens/mercados suportado na PoC).
- [ ] Modelar o schema do Postgres (tabelas da seção 4 do `CLAUDE.md`) e escrever as
      migrations iniciais.
- [ ] Definir o contrato de API entre Go e o serviço Python (schema JSON de request/response
      da otimização) — isso desacopla os dois times de trabalho mesmo sendo você sozinho.
- [ ] Montar esqueleto dos 3 serviços (API Go rodando, serviço Python respondendo "hello
      world" do CP-SAT com um exemplo trivial, Postgres com schema aplicado).
- [x] ~~Iniciar a coleta manual de preços~~. Substituída pela base do DIEESE (revisão de
      escopo de 2026-09-28).

**Entrega do mês:** repositório com os 3 serviços de pé, schema aplicado, e uma primeira
leva de dados reais de preço carregada no banco.

## Fase 2 — Modelagem Matemática e Design (Agosto)

- [ ] Implementar o modelo CP-SAT no serviço Python: variáveis `x[i][j]`, `y[j]`,
      restrições de estoque/atribuição, função objetivo ponderada (custo + conveniência).
- [ ] Começar simples: `custo_logistico = número de mercados visitados`. Só evoluir para
      distância/rota real se sobrar tempo (ver Fase 3).
- [ ] Escrever testes unitários do modelo com instâncias pequenas e resultado esperado
      conhecido manualmente (isso já prepara o terreno para a validação da Fase 4).
- [ ] Expor o endpoint `/otimizar` no FastAPI recebendo o contrato definido na Fase 1.
- [ ] Continuar/concluir o levantamento de dados.
- [ ] Desenhar as telas principais do frontend (wireframe simples): formulário de lista,
      tela de resultado.

**Entrega do mês:** endpoint de otimização funcional com dados reais de teste, retornando
alocação e custo total; testes unitários passando.

## Fase 3 — Prototipagem e Implementação (Setembro–Outubro)

- [ ] Implementar no Go: CRUD completo de listas/itens, chamada ao serviço Python,
      persistência da recomendação (tabela `recomendacoes`) para auditoria.
- [ ] Implementar o frontend PWA: cadastro de lista, disparo da recomendação, tela de
      resultado (mercados, itens por mercado, economia estimada vs. comprar tudo no
      mercado mais caro/único). Configurar manifest + service worker (instalável, funciona
      offline para telas estáticas no mínimo).
- [x] ~~Evoluir `custo_logistico` para distância real~~. Feito (circuito no CP-SAT) e
      depois revertido: na revisão de escopo de 2026-09-28 a distância saiu do objetivo. A
      ordem de visita agora é o vizinho mais próximo a partir da origem.
- [ ] Rodar os primeiros cenários de teste ponta a ponta (usuário cria lista → recomendação
      → visualização).

**Entrega do mês:** fluxo completo funcionando ponta a ponta com dados reais, ainda que
com interface simples.

## Fase 4 — Testes e Avaliação de Acurácia (Novembro–Dezembro)

- [ ] Script de validação por enumeração exaustiva para instâncias pequenas (poucos itens,
      poucos mercados) — comparar resultado com o CP-SAT e documentar convergência.
- [ ] Para instâncias maiores, montar cálculo manual documentado de 2–3 cenários de compra
      representativos (ex.: cesta básica completa) e comparar com a recomendação do
      sistema, registrando o ganho de economia/conveniência.
- [ ] Testes de sistema (happy path + casos de borda: item sem estoque em nenhum mercado,
      lista vazia, único mercado disponível).
- [ ] Consolidar os resultados em tabelas/gráficos para o capítulo de resultados do TCC.
- [ ] Fechamento do texto acadêmico e preparação da defesa.

**Entrega do mês:** relatório de validação (planilha ou markdown) com os cenários testados,
pronto para virar capítulo de resultados do TCC.

## Riscos e mitigação

- ~~**Coleta de preços real é o maior risco de atraso**~~. Eliminado: os preços vêm da base
  pública do DIEESE.
- **Escopo de rota/logística pode virar um projeto à parte.** Mitigação: manter a versão
  "nº de mercados visitados" como padrão e só evoluir para rota real se as Fases 1–3
  estiverem no prazo.
- **Ajuste de peso multiobjetivo é subjetivo.** Mitigação: definir 2–3 perfis fixos
  (ex.: "econômico", "equilibrado", "conveniente") em vez de um slider contínuo — mais
  fácil de validar e de explicar na defesa.
