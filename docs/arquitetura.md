# Arquitetura

## Visão geral

O sistema é dividido em quatro componentes, cada um com uma responsabilidade única. A
divisão não é enfeite: ela isola o núcleo de otimização — a contribuição acadêmica do
trabalho — de tudo que é acessório (autenticação, CRUD, interface).

```mermaid
flowchart LR
    U(["Usuário"])

    subgraph Cliente["Camada de apresentação"]
        PWA["PWA<br/>Vue 3 + Vite + TS<br/>porta 5173"]
    end

    subgraph Aplicacao["Camada de aplicação"]
        API["API REST<br/>Go 1.22 + Gin<br/>porta 8080"]
    end

    subgraph Otimizacao["Camada de decisão"]
        MOD["Serviço de otimização<br/>Python + FastAPI<br/>OR-Tools CP-SAT<br/>porta 8001"]
    end

    subgraph Dados["Camada de dados"]
        PG[("PostgreSQL 16<br/>porta 5432")]
    end

    U --> PWA
    PWA -->|"HTTPS / JSON"| API
    API -->|"HTTP interno / JSON"| MOD
    API -->|"SQL (pgx)"| PG
    MOD -.->|"não acessa o banco"| PG

    style MOD fill:#e8f0fe,stroke:#4a6fa5
    style PG fill:#f3f3f3,stroke:#888
```

A seta tracejada é intencional: o serviço Python **nunca** fala com o banco.

## Responsabilidades

| Componente | Responsabilidades | Não faz |
|---|---|---|
| **PWA** (`pwa/`) | formulário de lista, escolha de perfil, exibição da recomendação e da rota, instalação/offline do app shell | nenhuma regra de negócio ou cálculo de custo |
| **API Go** (`api/`) | autenticação, CRUD, montagem do payload de otimização, persistência da recomendação, formatação da resposta | não resolve o modelo matemático |
| **Serviço Python** (`modelo/`) | formulação e resolução do modelo CP-SAT, cálculo de distância, ordenação da rota, cálculo da economia | não tem estado, não conhece usuário, não acessa o banco |
| **PostgreSQL** | fonte única de verdade, histórico de preços, trilha de auditoria das recomendações | — |

## Por que o serviço de otimização é stateless

1. **Testabilidade.** O modelo é uma função pura de um JSON para outro. Cada teste de
   `modelo/testes/` monta uma instância pequena com ótimo conhecido à mão e verifica o
   resultado, sem banco, sem fixture e sem mock.
2. **Validação da Fase 4.** O `modelo/scripts/validacao_exaustiva.py` chama exatamente o
   mesmo código que a API chama em produção e o compara com enumeração exaustiva. Se o
   solver dependesse do banco, essa comparação exigiria montar um ambiente inteiro.
3. **Separação da contribuição acadêmica.** O capítulo de metodologia descreve o conteúdo
   de `modelo/app/otimizacao/`. Nada de infraestrutura se mistura ali.
4. **Substituibilidade.** Trocar a formulação, o solver ou os pesos não toca em uma linha
   de Go — o contrato em [`contrato-otimizacao.md`](contrato-otimizacao.md) é a fronteira.

## Fluxo completo de uma recomendação

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuário
    participant PWA as PWA
    participant API as API Go
    participant PG as PostgreSQL
    participant OTM as Otimizador Python

    U->>PWA: monta a lista e escolhe o perfil
    PWA->>API: POST /api/v1/listas/{id}/recomendacoes
    API->>API: valida o token JWT e a posse da lista
    API->>PG: SELECT itens_lista da lista
    API->>PG: SELECT candidatos em precos_vigentes
    API->>PG: SELECT mercados (coordenadas)
    PG-->>API: itens, precos, estoques, coordenadas

    Note over API: converte reais em centavos,<br/>traduz o perfil em peso_conveniencia

    API->>OTM: POST /otimizar
    OTM->>OTM: filtra candidatos por estoque suficiente
    OTM->>OTM: monta comprar[i][j], visitar[j], nao_atendido[i]
    OTM->>OTM: resolve com CP-SAT
    OTM->>OTM: ordena a rota dos mercados escolhidos
    OTM->>OTM: calcula o baseline de mercado único
    OTM-->>API: alocação, rota, custos, economia

    API->>PG: INSERT em recomendacoes (payload_resultado jsonb)
    API-->>PWA: recomendação formatada
    PWA-->>U: mercados na ordem da rota, itens e economia
```

## Decisões de arquitetura e seus motivos

| Decisão | Motivo | Consequência aceita |
|---|---|---|
| Dois serviços de backend em vez de um monólito | OR-Tools só existe de forma madura em Python/C++; a API se beneficia da concorrência e da tipagem do Go | um salto de rede extra por recomendação (irrelevante frente ao tempo de solve) |
| Só a API Go acessa o Postgres | evita duas fontes de acesso concorrente e mantém o otimizador puro | a API precisa montar um payload completo a cada chamada |
| Dinheiro em centavos inteiros no fio | CP-SAT é um solver **inteiro**; float em dinheiro produz erro de arredondamento acumulado | conversão explícita nas bordas, documentada no contrato |
| `precos` append-only | preserva a série histórica exigida pela fundamentação teórica do TCC | leitura passa pela view `precos_vigentes` |
| Distância por haversine, sem PostGIS | a PoC tem um raio pequeno e poucos mercados; haversine tem erro desprezível nessa escala | não considera malha viária real |
| Rota ordenada **após** o solve | manter a ordenação dentro do MILP transformaria o modelo em um TSP com seleção, fora do escopo da PoC | a distância usada no objetivo é uma linearização (ida e volta origem↔mercado) |
| Persistir `payload_resultado` como `jsonb` | trilha de auditoria para os testes de acurácia da Fase 4 sem criar tabelas de detalhe | duplicação controlada de dados |

## Portas, variáveis e execução

| Serviço | Porta | Variáveis principais |
|---|---|---|
| PWA | 5173 | `VITE_API_URL` |
| API Go | 8080 | `API_PORTA`, `BANCO_URL`, `OTIMIZADOR_URL`, `JWT_SEGREDO`, `ORIGEM_PADRAO_*` |
| Otimizador | 8001 | `MODELO_PORTA`, `MODELO_LIMITE_TEMPO_SEGUNDOS` |
| PostgreSQL | 5432 | `POSTGRES_USUARIO`, `POSTGRES_SENHA`, `POSTGRES_BANCO` |

Todas as variáveis têm exemplo em [`.env.exemplo`](../.env.exemplo). O passo a passo de
execução está em [`como-rodar.md`](como-rodar.md).

## Tratamento de falhas entre serviços

```mermaid
flowchart TD
    A["POST /listas/:id/recomendacoes"] --> B{"Otimizador respondeu?"}
    B -->|"Sim"| C{"Solver achou solução?"}
    B -->|"Timeout ou conexão recusada"| D["503 OTIMIZADOR_INDISPONIVEL"]
    C -->|"Sim"| E["201 com a recomendação"]
    C -->|"Nenhum item alocável"| F["201 com itens_nao_atendidos preenchido"]
    E --> G["INSERT em recomendacoes"]
    F --> G

    style D fill:#fde8e8,stroke:#c04
```

A API **nunca** devolve uma recomendação parcial ou estimada por conta própria quando o
otimizador falha: ou a resposta vem do solver, ou o cliente recebe `503`. Isso preserva a
rastreabilidade entre o que o usuário viu e o que o modelo matemático decidiu — requisito
para os experimentos da Fase 4.
