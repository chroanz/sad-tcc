-- =============================================================================
-- Migration 001 — Esquema inicial
-- Sistema de Apoio à Decisão para Compras de Supermercado (TCC)
--
-- Cria as oito tabelas do modelo mínimo viável (seção 4 do CLAUDE.md), seus
-- índices de apoio às consultas da API Go e a view `precos_vigentes`, que
-- expõe o snapshot de preço mais recente de cada par (marca, mercado) e é a
-- fonte dos candidatos enviados ao serviço de otimização em Python.
--
-- Premissas:
--   * PostgreSQL 16, sem PostGIS — a distância entre mercados é calculada por
--     haversine na aplicação, a partir de latitude/longitude.
--   * Valores monetários em NUMERIC(10,2); a conversão para centavos inteiros
--     (exigência do CP-SAT) é feita na aplicação, não no banco.
--   * `precos` é append-only: cada coleta gera um novo registro.
--   * Script idempotente e sem BEGIN/COMMIT — o runner de migrations da API Go
--     executa cada arquivo dentro de uma transação própria.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- usuarios
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id          BIGSERIAL   PRIMARY KEY,
    nome        TEXT        NOT NULL CHECK (length(btrim(nome)) > 0),
    email       TEXT        NOT NULL CHECK (position('@' IN email) > 1),
    senha_hash  TEXT        NOT NULL,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  usuarios            IS 'Usuários do sistema; dono das listas de compra.';
COMMENT ON COLUMN usuarios.senha_hash IS 'Hash da senha (bcrypt/argon2) gerado pela API Go. Nunca armazenar a senha em claro.';

CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_email ON usuarios (email);

-- -----------------------------------------------------------------------------
-- produtos
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS produtos (
    id         BIGSERIAL   PRIMARY KEY,
    nome       TEXT        NOT NULL CHECK (length(btrim(nome)) > 0),
    categoria  TEXT        NOT NULL CHECK (length(btrim(categoria)) > 0),
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  produtos           IS 'Item genérico da cesta, sem marca (ex.: "Arroz", "Feijão carioca").';
COMMENT ON COLUMN produtos.nome      IS 'Nome genérico do produto; único no catálogo da PoC.';
COMMENT ON COLUMN produtos.categoria IS 'Agrupamento de catálogo (ex.: "Mercearia", "Hortifruti") usado apenas para organizar a interface.';

CREATE UNIQUE INDEX IF NOT EXISTS ux_produtos_nome ON produtos (nome);

-- -----------------------------------------------------------------------------
-- marcas
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS marcas (
    id          BIGSERIAL   PRIMARY KEY,
    produto_id  BIGINT      NOT NULL REFERENCES produtos (id) ON DELETE CASCADE,
    nome        TEXT        NOT NULL CHECK (length(btrim(nome)) > 0),
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ux_marcas_produto_nome UNIQUE (produto_id, nome)
);

COMMENT ON TABLE  marcas            IS 'Variante comercial concreta de um produto (ex.: "Arroz Tio João 5kg"). É a unidade a que um preço se refere.';
COMMENT ON COLUMN marcas.produto_id IS 'Produto genérico ao qual a marca pertence; ON DELETE CASCADE porque a marca não existe fora do produto.';

CREATE INDEX IF NOT EXISTS ix_marcas_produto_id ON marcas (produto_id);

-- -----------------------------------------------------------------------------
-- mercados
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mercados (
    id         BIGSERIAL     PRIMARY KEY,
    nome       TEXT          NOT NULL CHECK (length(btrim(nome)) > 0),
    latitude   NUMERIC(9,6)  NOT NULL CHECK (latitude  BETWEEN -90  AND 90),
    longitude  NUMERIC(9,6)  NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    endereco   TEXT          NOT NULL CHECK (length(btrim(endereco)) > 0),
    criado_em  TIMESTAMPTZ   NOT NULL DEFAULT now()
);

COMMENT ON TABLE  mercados           IS 'Supermercados do recorte geográfico da PoC.';
COMMENT ON COLUMN mercados.latitude  IS 'Latitude em graus decimais (WGS84); usada no cálculo de haversine feito na aplicação.';
COMMENT ON COLUMN mercados.longitude IS 'Longitude em graus decimais (WGS84); usada no cálculo de haversine feito na aplicação.';

-- -----------------------------------------------------------------------------
-- precos  (append-only)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS precos (
    id                     BIGSERIAL      PRIMARY KEY,
    marca_id               BIGINT         NOT NULL REFERENCES marcas   (id) ON DELETE RESTRICT,
    mercado_id             BIGINT         NOT NULL REFERENCES mercados (id) ON DELETE RESTRICT,
    preco                  NUMERIC(10,2)  NOT NULL CHECK (preco > 0),
    unidade                TEXT           NOT NULL CHECK (unidade IN ('kg', 'g', 'L', 'ml', 'un')),
    quantidade_disponivel  NUMERIC(12,3)  NOT NULL CHECK (quantidade_disponivel >= 0),
    coletado_em            TIMESTAMPTZ    NOT NULL DEFAULT now()
);

COMMENT ON TABLE  precos                       IS 'Snapshot de preço e disponibilidade de uma marca em um mercado. Tabela APPEND-ONLY: cada coleta insere um novo registro e nenhum registro existente é atualizado ou removido, preservando a série histórica que fundamenta a análise do TCC. A leitura do preço corrente é feita pela view precos_vigentes.';
COMMENT ON COLUMN precos.preco                 IS 'Preço unitário observado, em reais. A conversão para centavos inteiros exigida pelo CP-SAT ocorre na aplicação.';
COMMENT ON COLUMN precos.unidade               IS 'Unidade de medida à qual o preço se refere (kg, g, L, ml, un).';
COMMENT ON COLUMN precos.quantidade_disponivel IS 'Estoque observado na coleta, na unidade da coluna unidade; limita a atribuição do item ao mercado no modelo de otimização. Zero significa item indisponível.';
COMMENT ON COLUMN precos.coletado_em           IS 'Momento da coleta. Define qual snapshot é o vigente e ordena a série histórica.';

CREATE INDEX IF NOT EXISTS ix_precos_marca_mercado_coleta
    ON precos (marca_id, mercado_id, coletado_em DESC);

CREATE INDEX IF NOT EXISTS ix_precos_mercado_id ON precos (mercado_id);

-- -----------------------------------------------------------------------------
-- listas_compra
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS listas_compra (
    id          BIGSERIAL   PRIMARY KEY,
    usuario_id  BIGINT      NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE,
    nome        TEXT        NOT NULL CHECK (length(btrim(nome)) > 0),
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE listas_compra IS 'Lista de compras de um usuário; entrada do processo de recomendação.';

CREATE INDEX IF NOT EXISTS ix_listas_compra_usuario_id ON listas_compra (usuario_id);

-- -----------------------------------------------------------------------------
-- itens_lista
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS itens_lista (
    id          BIGSERIAL      PRIMARY KEY,
    lista_id    BIGINT         NOT NULL REFERENCES listas_compra (id) ON DELETE CASCADE,
    produto_id  BIGINT         NOT NULL REFERENCES produtos      (id) ON DELETE RESTRICT,
    marca_id    BIGINT         NULL     REFERENCES marcas        (id) ON DELETE RESTRICT,
    quantidade  NUMERIC(12,3)  NOT NULL CHECK (quantidade > 0),
    unidade     TEXT           NOT NULL CHECK (unidade IN ('kg', 'g', 'L', 'ml', 'un'))
);

COMMENT ON TABLE  itens_lista            IS 'Item solicitado dentro de uma lista de compras; corresponde ao índice i das variáveis x[i][j] do modelo.';
COMMENT ON COLUMN itens_lista.marca_id   IS 'Marca exigida pelo usuário. NULL indica indiferença de marca: o otimizador pode escolher qualquer marca do produto.';
COMMENT ON COLUMN itens_lista.quantidade IS 'Quantidade desejada na unidade da coluna unidade; confrontada com precos.quantidade_disponivel na restrição de estoque.';

CREATE INDEX IF NOT EXISTS ix_itens_lista_lista_id ON itens_lista (lista_id);

-- -----------------------------------------------------------------------------
-- recomendacoes
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recomendacoes (
    id                             BIGSERIAL      PRIMARY KEY,
    lista_id                       BIGINT         NOT NULL REFERENCES listas_compra (id) ON DELETE CASCADE,
    gerado_em                      TIMESTAMPTZ    NOT NULL DEFAULT now(),
    custo_total                    NUMERIC(10,2)  NOT NULL CHECK (custo_total >= 0),
    parametro_peso_conveniencia    NUMERIC(6,3)   NOT NULL CHECK (parametro_peso_conveniencia >= 0),
    payload_resultado              JSONB          NOT NULL
);

COMMENT ON TABLE  recomendacoes                             IS 'Resultado persistido de uma execução do otimizador. Serve de trilha de auditoria para os testes de acurácia da Fase 4 (comparação CP-SAT vs. enumeração exaustiva).';
COMMENT ON COLUMN recomendacoes.custo_total                 IS 'Custo financeiro total da alocação recomendada, em reais, reconvertido de centavos pela aplicação.';
COMMENT ON COLUMN recomendacoes.parametro_peso_conveniencia IS 'Peso da parcela logística na função objetivo min custo_total(x) + peso * custo_logistico(y). Registrado para reproduzir a execução.';
COMMENT ON COLUMN recomendacoes.payload_resultado           IS 'Resposta JSON completa do serviço de otimização (alocação item/mercado, mercados visitados, status do solver, tempo de resolução). Guardado na íntegra para auditoria e reprodutibilidade.';

CREATE INDEX IF NOT EXISTS ix_recomendacoes_lista_gerado
    ON recomendacoes (lista_id, gerado_em DESC);

-- -----------------------------------------------------------------------------
-- View precos_vigentes — snapshot mais recente por (marca_id, mercado_id)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW precos_vigentes AS
SELECT DISTINCT ON (p.marca_id, p.mercado_id)
       p.id AS preco_id,
       p.marca_id,
       p.mercado_id,
       p.preco,
       p.unidade,
       p.quantidade_disponivel,
       p.coletado_em
  FROM precos p
 ORDER BY p.marca_id, p.mercado_id, p.coletado_em DESC;

COMMENT ON VIEW precos_vigentes IS 'Último snapshot de preço/disponibilidade de cada par (marca, mercado). É a fonte dos candidatos que a API Go monta para o payload de otimização; a tabela precos permanece intacta como série histórica.';
