# Fluxo da recomendação

O caminho completo de `POST /api/v1/listas/:id/recomendacoes`, que é a razão de existir do
sistema. Implementado em [`internal/servico/recomendacao.go`](../internal/servico/recomendacao.go).

## Sequência completa

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuário
    participant PWA as PWA
    participant T as transporte
    participant S as servico.Recomendacao
    participant R as repositorio
    participant PG as PostgreSQL
    participant O as otimizador.Cliente
    participant PY as Serviço Python

    U->>PWA: escolhe o perfil e pede a recomendação
    PWA->>T: POST /listas/3/recomendacoes
    T->>T: middleware valida o JWT
    T->>S: Gerar(listaID, usuarioID, pedido)

    S->>R: BuscarLista + ListarItens
    R->>PG: SELECT
    PG-->>R: lista e itens
    R-->>S: lista com itens
    S->>S: confere posse (403 se for de outro usuário)

    S->>S: resolverPeso (perfil ou peso livre)
    S->>S: valida o teto 20 itens
    S->>R: ListarMercados
    R->>PG: SELECT mercados
    S->>S: valida o teto 8 mercados
    S->>S: resolverOrigem (informada ou padrão)

    S->>R: BuscarOfertasVigentes(produtoIDs)
    R->>PG: SELECT em precos_vigentes
    PG-->>R: ofertas
    R->>R: preco::text convertido em centavos
    R-->>S: ofertas vigentes

    S->>S: monta candidatos por item
    S->>O: Otimizar(requisicao)
    O->>PY: POST /otimizar
    PY->>PY: CP-SAT em duas fases + rota + economia
    PY-->>O: resposta
    O-->>S: resposta + payload bruto

    S->>R: SalvarRecomendacao(payload jsonb)
    R->>PG: INSERT em recomendacoes
    PG-->>R: id, gerado_em

    S->>S: enriquece com produto_nome e endereço
    S-->>T: RecomendacaoGerada
    T-->>PWA: 201 Created
    PWA-->>U: mercados na ordem da rota e economia
```

## Os dez passos, em detalhe

### 1–3. Posse e limites
A lista é carregada com os itens e a posse é conferida. Lista de outro usuário responde
**403**, não 404 — decisão do contrato REST.

Em seguida vêm os tetos da PoC: mais de **20 itens** ou mais de **8 mercados** cadastrados
resultam em `400 VALIDACAO` com mensagem descritiva. A instância nunca é processada
parcialmente.

### 4. Peso da conveniência

```mermaid
flowchart TD
    A["pedido"] --> B{"peso_conveniencia veio?"}
    B -->|"Sim"| C{"peso maior ou igual a zero?"}
    C -->|"Sim"| D["usa o peso livre<br/>rótulo do perfil, se houver"]
    C -->|"Não"| E["400 VALIDACAO"]
    B -->|"Não"| F{"perfil veio?"}
    F -->|"Sim"| G["economico=0, equilibrado=1, conveniente=3"]
    F -->|"Não"| E

    style D fill:#eef7e8,stroke:#5a8a4a
    style G fill:#eef7e8,stroke:#5a8a4a
```

O peso numérico livre **sobrepõe** o perfil. É o que permite varrer a fronteira de Pareto
nos experimentos da Fase 4 sem alterar código nem inventar perfis novos.

### 5. Origem
Usa a coordenada enviada pelo cliente ou, na ausência dela, `ORIGEM_PADRAO_LATITUDE` e
`ORIGEM_PADRAO_LONGITUDE` — o centro de Juazeiro do Norte. Nesse caso a resposta traz
`origem_aproximada: true`, para o PWA poder avisar que a distância é estimada.

### 6. Candidatos — a consulta que sustenta o modelo

A leitura vem da **view `precos_vigentes`**, nunca da tabela `precos`. A view devolve o
snapshot mais recente de cada par (marca, mercado); ler a tabela crua faria uma coleta
antiga concorrer com a atual dentro do modelo.

```sql
SELECT ma.produto_id, pv.marca_id, ma.nome, pv.mercado_id,
       pv.preco::text, pv.quantidade_disponivel::float8, pv.unidade
  FROM precos_vigentes pv
  JOIN marcas ma ON ma.id = pv.marca_id
 WHERE ma.produto_id = ANY($1::bigint[])
```

Uma única consulta para todos os produtos da lista — não uma por item.

### 7. Marca fixa versus marca livre

```mermaid
flowchart TD
    A["Item da lista"] --> B{"marca_id informado?"}
    B -->|"Sim"| C["só aquela marca é candidata"]
    B -->|"Não (NULL)"| D["todas as marcas do produto concorrem"]
    D --> E{"várias marcas no mesmo mercado?"}
    E -->|"Sim"| F["escolhe uma: primeiro quem<br/>atende a quantidade, depois a mais barata"]
    E -->|"Não"| G["candidato único"]
    C --> H["candidatos do item"]
    F --> H
    G --> H
    H --> I["ordenados por mercado_id<br/>payload determinístico"]
```

O contrato de otimização admite **um único candidato por par (item, mercado)**. Com marca
livre, várias marcas do mesmo produto disputam o mesmo mercado, e `melhorCandidato` decide:
quem atende a quantidade pedida sempre vence quem não atende; entre equivalentes, vence a
mais barata.

Candidatos com estoque insuficiente **são enviados assim mesmo**. Descartá-los aqui
impediria o otimizador de distinguir `SEM_CANDIDATO` (não existe preço) de
`SEM_CANDIDATO_COM_ESTOQUE` (existe preço, falta estoque) — e essa distinção é o que o
usuário precisa ver para saber se o problema é de catálogo ou de disponibilidade.

### 8. Chamada ao otimizador
Com timeout de `OTIMIZADOR_TIMEOUT_SEGUNDOS` e `context.Context` propagado. Timeout,
conexão recusada ou 5xx viram `ErrOtimizadorIndisponivel` → **503**.

A API **nunca** devolve uma recomendação parcial ou estimada por conta própria quando o
otimizador falha. Isso preserva a rastreabilidade entre o que o usuário viu e o que o
modelo matemático decidiu.

### 9. Persistência para auditoria
O `payload_resultado` guarda a resposta **bruta** do otimizador, em `jsonb`. Com ele e a
semente fixa do solver, qualquer execução futura do mesmo código reproduz o resultado — é
o que torna a trilha da Fase 4 verificável, e não apenas registrada.

### 10. Enriquecimento
O otimizador não conhece nome de produto nem endereço de mercado — ele recebe apenas
identificadores, preços e coordenadas. A API reanexa `produto_nome` e `endereco` a partir
dos dados que já tem em memória, sem consulta extra.

## Reabrir uma recomendação

`GET /recomendacoes/:id` reconstrói a resposta a partir do `payload_resultado` gravado.
**Nunca recalcula.** Recomendações são imutáveis: só assim é possível comparar a mesma
lista sob perfis diferentes, ou ao longo de coletas de preço diferentes, sem que o passado
mude sob os pés do experimento.
