-- =============================================================================
-- Migration 002 — Dados de semente (DADOS FICTÍCIOS)
-- Sistema de Apoio à Decisão para Compras de Supermercado (TCC)
--
-- ############################################################################
-- #  ATENÇÃO: TODOS OS DADOS DESTE ARQUIVO SÃO FICTÍCIOS.                     #
-- #                                                                          #
-- #  Mercados, endereços, coordenadas, marcas, preços e estoques foram        #
-- #  fabricados para que a PoC rode ponta a ponta (lista -> otimizador ->     #
-- #  recomendação) antes de a coleta manual de campo estar concluída.         #
-- #  NENHUM preço aqui foi observado em loja. Nenhum estabelecimento real     #
-- #  é representado: os nomes são placeholders.                               #
-- #                                                                          #
-- #  Estes dados DEVEM ser substituídos pela coleta real (ver                 #
-- #  docs/dados-e-coleta.md e dados/README.md). O procedimento é apagar as    #
-- #  linhas de `precos` desta semente OU simplesmente inserir as coletas      #
-- #  reais com `coletado_em` posterior: como `precos` é append-only e a view  #
-- #  `precos_vigentes` seleciona o snapshot mais recente, a coleta real       #
-- #  passa a prevalecer automaticamente.                                      #
-- ############################################################################
--
-- Recorte geográfico: Juazeiro do Norte/CE, raio de ~7 km do centro
-- (-7.2131, -39.3153). 6 mercados, 18 produtos de cesta básica, 36 marcas
-- (2 por produto), 218 snapshots de preço em duas datas de coleta
-- (24 em 2026-08-25 e 194 em 2026-09-01).
--
-- Propriedades intencionais do conjunto (ver docs/dados-e-coleta.md, seção
-- "Características intencionais"):
--   * Nenhum mercado é o mais barato em todas as marcas — cada um vence em
--     pelo menos duas.
--   * Os mercados mais baratos são os mais distantes do centro; os mais caros,
--     os mais próximos. É esse gradiente que cria o trade-off custo x
--     conveniência que a função objetivo resolve.
--   * A dispersão de preço da mesma marca entre mercados fica entre ~10% e
--     ~30% (faixa realista, não artificial).
--   * Lacunas de cobertura propositais: "Carne bovina (patinho)" existe em
--     apenas 2 mercados e "Banana prata" em 3; nenhum mercado sozinho cobre os
--     18 produtos (o baseline "comprar tudo em um único mercado" fica
--     insatisfazível para a cesta completa, exercitando o caminho de
--     comparação parcial).
--   * Duas marcas com quantidade_disponivel = 0 (indisponíveis) e duas com
--     estoque de 1 e 2 unidades, para exercitar a restrição de estoque
--     suficiente e o caminho de "item não atendido".
--
-- Premissas de execução:
--   * Requer 001_esquema_inicial.sql aplicado.
--   * Sem BEGIN/COMMIT — o runner de migrations da API Go executa cada arquivo
--     dentro de uma transação própria.
--   * IDEMPOTENTE: rodar duas vezes não duplica nem falha. Como as PKs são
--     BIGSERIAL, nenhum id é fixado no script; todas as FKs são resolvidas por
--     nome (subconsulta/junção). Onde o esquema tem unicidade
--     (usuarios.email, produtos.nome, marcas(produto_id, nome)) usa-se
--     ON CONFLICT DO NOTHING; onde não há (mercados, precos, listas_compra,
--     itens_lista) usa-se um anti-join WHERE NOT EXISTS.
--   * Todos os valores respeitam os CHECKs de 001: unidade IN
--     ('kg','g','L','ml','un'), preco > 0, quantidade_disponivel >= 0,
--     quantidade > 0, latitude/longitude dentro dos limites e textos não
--     vazios.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Mercados
--
-- Seis pontos distintos, espalhados por bairros de Juazeiro do Norte dentro de ~7 km
-- do centro. A distância ao centro (haversine) está anotada porque é ela que
-- alimenta o custo logístico do modelo, e a ordenação preço x distância é
-- deliberada: quanto mais longe, mais barato.
-- `mercados` não tem índice único em `nome`, então a idempotência aqui é feita
-- por anti-join.
-- -----------------------------------------------------------------------------
INSERT INTO mercados (nome, latitude, longitude, endereco)
SELECT d.nome, d.latitude, d.longitude, d.endereco
  FROM (
      VALUES
          -- ~0.2 km do centro
          ('Mercado Central do Juazeiro', -7.214500::numeric(9,6), -39.316800::numeric(9,6), 'R. São Pedro, 210 - Centro, Juazeiro do Norte/CE'),
          -- ~1.1 km do centro
          ('Supermercado Bom Preço Triângulo', -7.204200, -39.320500, 'Av. Padre Cícero, 1450 - Triângulo, Juazeiro do Norte/CE'),
          -- ~1.5 km do centro
          ('Supermercado Vila Nova Salesianos', -7.220800, -39.304200, 'Av. Ailton Gomes, 980 - Salesianos, Juazeiro do Norte/CE'),
          -- ~2.9 km do centro
          ('Hipermercado Lagoa Seca', -7.235000, -39.330000, 'Av. Leão Sampaio, 2100 - Lagoa Seca, Juazeiro do Norte/CE'),
          -- ~5.1 km do centro
          ('Atacadão do Limoeiro', -7.247000, -39.346000, 'Av. Plácido Aderaldo Castelo, 3400 - Limoeiro, Juazeiro do Norte/CE'),
          -- ~6.9 km do centro
          ('Supermercado Economia Muriti', -7.264000, -39.279000, 'R. Interventor Manoel do Nascimento Veras, 620 - Muriti, Juazeiro do Norte/CE')
  ) AS d(nome, latitude, longitude, endereco)
 WHERE NOT EXISTS (
       SELECT 1 FROM mercados m WHERE m.nome = d.nome
 );

-- -----------------------------------------------------------------------------
-- 2. Produtos (18 itens genéricos de cesta básica nacional)
-- `ux_produtos_nome` garante a unicidade — ON CONFLICT resolve a idempotência.
-- -----------------------------------------------------------------------------
INSERT INTO produtos (nome, categoria)
VALUES
    ('Arroz', 'Mercearia'),
    ('Feijão carioca', 'Mercearia'),
    ('Óleo de soja', 'Mercearia'),
    ('Açúcar refinado', 'Mercearia'),
    ('Café torrado e moído', 'Mercearia'),
    ('Leite integral UHT', 'Laticínios'),
    ('Farinha de trigo', 'Mercearia'),
    ('Macarrão espaguete', 'Mercearia'),
    ('Sal refinado', 'Mercearia'),
    ('Molho de tomate', 'Mercearia'),
    ('Biscoito cream cracker', 'Mercearia'),
    ('Margarina', 'Laticínios'),
    ('Ovos de galinha', 'Frios e ovos'),
    ('Sabonete', 'Higiene pessoal'),
    ('Papel higiênico', 'Higiene pessoal'),
    ('Detergente líquido', 'Limpeza'),
    ('Carne bovina (patinho)', 'Açougue'),
    ('Banana prata', 'Hortifruti')
ON CONFLICT (nome) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 3. Marcas (2 por produto, 36 no total)
--
-- O nome da marca carrega o peso/volume da embalagem, porque é a embalagem —
-- e não o produto genérico — que tem preço. `produto_id` é resolvido por
-- junção com `produtos.nome`, nunca por id literal.
-- -----------------------------------------------------------------------------
INSERT INTO marcas (produto_id, nome)
SELECT p.id, d.marca
  FROM (
      VALUES
          ('Arroz', 'Tio João 5kg'),
          ('Arroz', 'Camil 5kg'),
          ('Feijão carioca', 'Kicaldo 1kg'),
          ('Feijão carioca', 'Camil 1kg'),
          ('Óleo de soja', 'Soya 900ml'),
          ('Óleo de soja', 'Liza 900ml'),
          ('Açúcar refinado', 'União 1kg'),
          ('Açúcar refinado', 'Caravelas 1kg'),
          ('Café torrado e moído', 'Pilão 500g'),
          ('Café torrado e moído', 'Melitta 500g'),
          ('Leite integral UHT', 'Itambé 1L'),
          ('Leite integral UHT', 'Piracanjuba 1L'),
          ('Farinha de trigo', 'Dona Benta 1kg'),
          ('Farinha de trigo', 'Renata 1kg'),
          ('Macarrão espaguete', 'Renata 500g'),
          ('Macarrão espaguete', 'Adria 500g'),
          ('Sal refinado', 'Cisne 1kg'),
          ('Sal refinado', 'Lebre 1kg'),
          ('Molho de tomate', 'Quero 340g'),
          ('Molho de tomate', 'Elefante 340g'),
          ('Biscoito cream cracker', 'Piraquê 200g'),
          ('Biscoito cream cracker', 'Bauducco 200g'),
          ('Margarina', 'Qualy 500g'),
          ('Margarina', 'Doriana 500g'),
          ('Ovos de galinha', 'Mantiqueira 12un'),
          ('Ovos de galinha', 'Granja Faria 12un'),
          ('Sabonete', 'Dove 90g'),
          ('Sabonete', 'Protex 85g'),
          ('Papel higiênico', 'Neve 12 rolos 30m'),
          ('Papel higiênico', 'Personal 12 rolos 30m'),
          ('Detergente líquido', 'Ypê 500ml'),
          ('Detergente líquido', 'Limpol 500ml'),
          ('Carne bovina (patinho)', 'Friboi Patinho 1kg'),
          ('Carne bovina (patinho)', 'Minerva Patinho 1kg'),
          ('Banana prata', 'Prata Granel 1kg'),
          ('Banana prata', 'Prata Bandeja 1kg')
  ) AS d(produto, marca)
  JOIN produtos p ON p.nome = d.produto
ON CONFLICT (produto_id, nome) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 4. Preços — coleta de 2026-08-25 (histórica)
--
-- Subconjunto de 4 marcas de alta rotatividade (Arroz Tio João 5kg, Feijão
-- Kicaldo 1kg, Café Pilão 500g e Leite Itambé 1L) em todos os 6 mercados.
-- Existe para que a série histórica de `precos` não seja um ponto único e para
-- demonstrar, na prática, que `precos_vigentes` descarta o snapshot antigo.
--
-- Os horários de coleta são distintos por mercado e por data: a view
-- `precos_vigentes` usa DISTINCT ON ... ORDER BY coletado_em DESC e NÃO
-- desempata `coletado_em` idênticos, então dois snapshots do mesmo par
-- (marca, mercado) nunca podem compartilhar o mesmo instante.
--
-- Nota de leitura: o Café Pilão 500g aparece aqui com 24 unidades no
-- Supermercado Economia Muriti e com 0 na coleta de 2026-09-01 —
-- ruptura de estoque preservada na série, e não sobrescrita.
--
-- `precos` é append-only e não tem chave única; a idempotência é o anti-join
-- por (marca_id, mercado_id, coletado_em).
-- -----------------------------------------------------------------------------
WITH dados (mercado_nome, produto_nome, marca_nome, preco, unidade, quantidade_disponivel, coletado_em) AS (
    VALUES
        ('Mercado Central do Juazeiro', 'Arroz', 'Tio João 5kg', 30.31::numeric(10,2), 'un', 29.000::numeric(12,3), TIMESTAMPTZ '2026-08-25 08:25:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Arroz', 'Tio João 5kg', 29.25, 'un', 44.000, '2026-08-25 09:40:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Arroz', 'Tio João 5kg', 29.60, 'un', 28.000, '2026-08-25 10:15:00-03'),
        ('Hipermercado Lagoa Seca', 'Arroz', 'Tio João 5kg', 24.92, 'un', 84.000, '2026-08-25 11:50:00-03'),
        ('Atacadão do Limoeiro', 'Arroz', 'Tio João 5kg', 25.43, 'un', 119.000, '2026-08-25 14:20:00-03'),
        ('Supermercado Economia Muriti', 'Arroz', 'Tio João 5kg', 26.39, 'un', 43.000, '2026-08-25 16:30:00-03'),
        ('Mercado Central do Juazeiro', 'Feijão carioca', 'Kicaldo 1kg', 9.79, 'un', 25.000, '2026-08-25 08:25:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Feijão carioca', 'Kicaldo 1kg', 9.08, 'un', 28.000, '2026-08-25 09:40:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Feijão carioca', 'Kicaldo 1kg', 8.57, 'un', 35.000, '2026-08-25 10:15:00-03'),
        ('Hipermercado Lagoa Seca', 'Feijão carioca', 'Kicaldo 1kg', 8.05, 'un', 110.000, '2026-08-25 11:50:00-03'),
        ('Atacadão do Limoeiro', 'Feijão carioca', 'Kicaldo 1kg', 7.35, 'un', 145.000, '2026-08-25 14:20:00-03'),
        ('Supermercado Economia Muriti', 'Feijão carioca', 'Kicaldo 1kg', 7.79, 'un', 38.000, '2026-08-25 16:30:00-03'),
        ('Mercado Central do Juazeiro', 'Café torrado e moído', 'Pilão 500g', 21.96, 'un', 28.000, '2026-08-25 08:25:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Café torrado e moído', 'Pilão 500g', 21.86, 'un', 43.000, '2026-08-25 09:40:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Café torrado e moído', 'Pilão 500g', 20.79, 'un', 37.000, '2026-08-25 10:15:00-03'),
        ('Hipermercado Lagoa Seca', 'Café torrado e moído', 'Pilão 500g', 17.87, 'un', 117.000, '2026-08-25 11:50:00-03'),
        ('Atacadão do Limoeiro', 'Café torrado e moído', 'Pilão 500g', 18.24, 'un', 102.000, '2026-08-25 14:20:00-03'),
        ('Supermercado Economia Muriti', 'Café torrado e moído', 'Pilão 500g', 18.59, 'un', 24, '2026-08-25 16:30:00-03'),
        ('Mercado Central do Juazeiro', 'Leite integral UHT', 'Itambé 1L', 6.10, 'un', 24.000, '2026-08-25 08:25:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Leite integral UHT', 'Itambé 1L', 5.16, 'un', 27.000, '2026-08-25 09:40:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Leite integral UHT', 'Itambé 1L', 5.89, 'un', 25.000, '2026-08-25 10:15:00-03'),
        ('Hipermercado Lagoa Seca', 'Leite integral UHT', 'Itambé 1L', 5.34, 'un', 72.000, '2026-08-25 11:50:00-03'),
        ('Atacadão do Limoeiro', 'Leite integral UHT', 'Itambé 1L', 5.22, 'un', 128.000, '2026-08-25 14:20:00-03'),
        ('Supermercado Economia Muriti', 'Leite integral UHT', 'Itambé 1L', 5.44, 'un', 49.000, '2026-08-25 16:30:00-03')
)
INSERT INTO precos (marca_id, mercado_id, preco, unidade, quantidade_disponivel, coletado_em)
SELECT ma.id, me.id, d.preco, d.unidade, d.quantidade_disponivel, d.coletado_em
  FROM dados d
  JOIN mercados me ON me.nome = d.mercado_nome
  JOIN produtos pr ON pr.nome = d.produto_nome
  JOIN marcas   ma ON ma.produto_id = pr.id AND ma.nome = d.marca_nome
 WHERE NOT EXISTS (
       SELECT 1
         FROM precos p
        WHERE p.marca_id   = ma.id
          AND p.mercado_id = me.id
          AND p.coletado_em = d.coletado_em
 );

-- -----------------------------------------------------------------------------
-- 5. Preços — coleta de 2026-09-01 (vigente)
--
-- Cobertura completa: toda combinação marca x mercado que o mercado oferta.
-- Ausência de linha = o mercado não trabalha com aquele produto (lacuna de
-- catálogo). Linha com quantidade_disponivel = 0 = o mercado trabalha com o
-- produto mas está em ruptura de estoque nesta coleta — essa distinção é
-- semântica e proposital.
--
-- Estoques atípicos embutidos de propósito:
--   * Café Pilão 500g  @ Supermercado Economia Muriti  -> 0   (ruptura)
--   * Margarina Doriana 500g @ Hipermercado Lagoa Seca        -> 0   (ruptura)
--   * Arroz Camil 5kg  @ Atacadão do Limoeiro                    -> 2   (estoque baixo)
--   * Leite Piracanjuba 1L @ Mercado Central do Juazeiro       -> 1   (estoque baixo)
-- -----------------------------------------------------------------------------
WITH dados (mercado_nome, produto_nome, marca_nome, preco, unidade, quantidade_disponivel, coletado_em) AS (
    VALUES
        ('Mercado Central do Juazeiro', 'Arroz', 'Tio João 5kg', 31.25::numeric(10,2), 'un', 23.000::numeric(12,3), TIMESTAMPTZ '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Arroz', 'Tio João 5kg', 29.85, 'un', 38.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Arroz', 'Tio João 5kg', 29.02, 'un', 22.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Arroz', 'Tio João 5kg', 25.96, 'un', 78.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Arroz', 'Tio João 5kg', 25.18, 'un', 113.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Arroz', 'Tio João 5kg', 26.66, 'un', 37.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Arroz', 'Camil 5kg', 29.01, 'un', 21.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Arroz', 'Camil 5kg', 27.71, 'un', 30.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Arroz', 'Camil 5kg', 26.94, 'un', 35.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Arroz', 'Camil 5kg', 24.10, 'un', 91.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Arroz', 'Camil 5kg', 23.37, 'un', 2.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Arroz', 'Camil 5kg', 24.75, 'un', 50.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Feijão carioca', 'Kicaldo 1kg', 9.41, 'un', 19.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Feijão carioca', 'Kicaldo 1kg', 8.99, 'un', 22.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Feijão carioca', 'Kicaldo 1kg', 8.74, 'un', 29.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Feijão carioca', 'Kicaldo 1kg', 7.82, 'un', 104.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Feijão carioca', 'Kicaldo 1kg', 7.58, 'un', 139.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Feijão carioca', 'Kicaldo 1kg', 7.64, 'un', 32.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Feijão carioca', 'Camil 1kg', 9.97, 'un', 17.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Feijão carioca', 'Camil 1kg', 9.52, 'un', 35.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Feijão carioca', 'Camil 1kg', 9.26, 'un', 23.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Feijão carioca', 'Camil 1kg', 8.28, 'un', 117.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Feijão carioca', 'Camil 1kg', 8.03, 'un', 152.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Feijão carioca', 'Camil 1kg', 8.10, 'un', 45.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Óleo de soja', 'Soya 900ml', 7.95, 'un', 15.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Óleo de soja', 'Soya 900ml', 7.60, 'un', 27.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Óleo de soja', 'Soya 900ml', 7.38, 'un', 36.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Óleo de soja', 'Soya 900ml', 6.14, 'un', 59.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Óleo de soja', 'Soya 900ml', 6.41, 'un', 165.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Óleo de soja', 'Soya 900ml', 6.46, 'un', 58.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Óleo de soja', 'Liza 900ml', 8.40, 'un', 13.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Óleo de soja', 'Liza 900ml', 8.03, 'un', 40.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Óleo de soja', 'Liza 900ml', 7.80, 'un', 30.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Óleo de soja', 'Liza 900ml', 6.49, 'un', 72.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Óleo de soja', 'Liza 900ml', 6.77, 'un', 178.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Óleo de soja', 'Liza 900ml', 6.83, 'un', 40.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Açúcar refinado', 'União 1kg', 5.94, 'un', 11.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Açúcar refinado', 'União 1kg', 5.67, 'un', 32.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Açúcar refinado', 'União 1kg', 5.51, 'un', 24.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Açúcar refinado', 'União 1kg', 4.93, 'un', 85.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Açúcar refinado', 'União 1kg', 5.07, 'un', 191.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Açúcar refinado', 'União 1kg', 4.82, 'un', 53.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Açúcar refinado', 'Caravelas 1kg', 5.26, 'un', 24.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Açúcar refinado', 'Caravelas 1kg', 5.03, 'un', 24.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Açúcar refinado', 'Caravelas 1kg', 4.89, 'un', 18.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Açúcar refinado', 'Caravelas 1kg', 4.37, 'un', 98.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Açúcar refinado', 'Caravelas 1kg', 4.50, 'un', 83.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Açúcar refinado', 'Caravelas 1kg', 4.28, 'un', 35.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Café torrado e moído', 'Pilão 500g', 23.36, 'un', 22.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Café torrado e moído', 'Pilão 500g', 23.01, 'un', 37.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Café torrado e moído', 'Pilão 500g', 22.36, 'un', 31.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Café torrado e moído', 'Pilão 500g', 18.61, 'un', 111.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Café torrado e moído', 'Pilão 500g', 19.40, 'un', 96.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Café torrado e moído', 'Pilão 500g', 19.57, 'un', 0.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Café torrado e moído', 'Melitta 500g', 21.62, 'un', 20.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Café torrado e moído', 'Melitta 500g', 21.29, 'un', 29.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Café torrado e moído', 'Melitta 500g', 20.70, 'un', 25.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Café torrado e moído', 'Melitta 500g', 17.22, 'un', 53.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Café torrado e moído', 'Melitta 500g', 16.88, 'un', 109.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Café torrado e moído', 'Melitta 500g', 18.11, 'un', 30.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Leite integral UHT', 'Itambé 1L', 6.16, 'un', 18.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Leite integral UHT', 'Itambé 1L', 5.06, 'un', 21.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Leite integral UHT', 'Itambé 1L', 5.72, 'un', 19.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Leite integral UHT', 'Itambé 1L', 5.45, 'un', 66.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Leite integral UHT', 'Itambé 1L', 5.17, 'un', 122.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Leite integral UHT', 'Itambé 1L', 5.61, 'un', 43.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Leite integral UHT', 'Piracanjuba 1L', 6.50, 'un', 1.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Leite integral UHT', 'Piracanjuba 1L', 5.34, 'un', 34.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Leite integral UHT', 'Piracanjuba 1L', 6.03, 'un', 32.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Leite integral UHT', 'Piracanjuba 1L', 5.74, 'un', 79.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Leite integral UHT', 'Piracanjuba 1L', 5.45, 'un', 135.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Leite integral UHT', 'Piracanjuba 1L', 5.91, 'un', 56.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Farinha de trigo', 'Dona Benta 1kg', 5.71, 'un', 14.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Farinha de trigo', 'Dona Benta 1kg', 5.46, 'un', 26.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Farinha de trigo', 'Dona Benta 1kg', 5.30, 'un', 26.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Farinha de trigo', 'Dona Benta 1kg', 4.75, 'un', 92.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Farinha de trigo', 'Dona Benta 1kg', 4.60, 'un', 148.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Farinha de trigo', 'Dona Benta 1kg', 4.64, 'un', 38.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Farinha de trigo', 'Renata 1kg', 5.26, 'un', 12.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Farinha de trigo', 'Renata 1kg', 5.03, 'un', 39.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Farinha de trigo', 'Renata 1kg', 4.89, 'un', 20.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Farinha de trigo', 'Renata 1kg', 4.37, 'un', 105.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Farinha de trigo', 'Renata 1kg', 4.24, 'un', 161.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Farinha de trigo', 'Renata 1kg', 4.28, 'un', 51.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Macarrão espaguete', 'Renata 500g', 5.04, 'un', 10.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Macarrão espaguete', 'Renata 500g', 4.82, 'un', 31.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Macarrão espaguete', 'Renata 500g', 3.98, 'un', 33.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Macarrão espaguete', 'Renata 500g', 4.19, 'un', 118.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Macarrão espaguete', 'Renata 500g', 4.06, 'un', 174.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Macarrão espaguete', 'Renata 500g', 4.10, 'un', 33.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Macarrão espaguete', 'Adria 500g', 5.60, 'un', 23.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Macarrão espaguete', 'Adria 500g', 5.35, 'un', 23.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Macarrão espaguete', 'Adria 500g', 4.42, 'un', 27.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Macarrão espaguete', 'Adria 500g', 4.65, 'un', 60.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Macarrão espaguete', 'Adria 500g', 4.51, 'un', 187.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Macarrão espaguete', 'Adria 500g', 4.55, 'un', 46.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Sal refinado', 'Cisne 1kg', 2.42, 'un', 21.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Sal refinado', 'Cisne 1kg', 2.89, 'un', 36.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Sal refinado', 'Cisne 1kg', 2.81, 'un', 21.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Sal refinado', 'Cisne 1kg', 2.51, 'un', 73.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Sal refinado', 'Cisne 1kg', 2.44, 'un', 200.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Sal refinado', 'Cisne 1kg', 2.46, 'un', 59.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Sal refinado', 'Lebre 1kg', 2.06, 'un', 19.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Sal refinado', 'Lebre 1kg', 2.46, 'un', 28.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Sal refinado', 'Lebre 1kg', 2.39, 'un', 34.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Sal refinado', 'Lebre 1kg', 2.14, 'un', 86.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Sal refinado', 'Lebre 1kg', 2.08, 'un', 92.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Sal refinado', 'Lebre 1kg', 2.09, 'un', 41.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Molho de tomate', 'Quero 340g', 3.92, 'un', 17.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Molho de tomate', 'Quero 340g', 3.07, 'un', 20.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Molho de tomate', 'Quero 340g', 3.64, 'un', 28.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Molho de tomate', 'Quero 340g', 3.26, 'un', 99.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Molho de tomate', 'Quero 340g', 3.16, 'un', 105.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Molho de tomate', 'Quero 340g', 3.19, 'un', 54.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Molho de tomate', 'Elefante 340g', 4.26, 'un', 15.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Molho de tomate', 'Elefante 340g', 3.33, 'un', 33.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Molho de tomate', 'Elefante 340g', 3.95, 'un', 22.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Molho de tomate', 'Elefante 340g', 3.54, 'un', 112.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Molho de tomate', 'Elefante 340g', 3.43, 'un', 118.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Molho de tomate', 'Elefante 340g', 3.46, 'un', 36.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Biscoito cream cracker', 'Piraquê 200g', 5.38, 'un', 13.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Biscoito cream cracker', 'Piraquê 200g', 4.99, 'un', 35.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Biscoito cream cracker', 'Piraquê 200g', 4.47, 'un', 54.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Biscoito cream cracker', 'Piraquê 200g', 4.33, 'un', 131.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Biscoito cream cracker', 'Piraquê 200g', 4.37, 'un', 49.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Biscoito cream cracker', 'Bauducco 200g', 5.82, 'un', 11.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Biscoito cream cracker', 'Bauducco 200g', 5.41, 'un', 29.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Biscoito cream cracker', 'Bauducco 200g', 4.84, 'un', 67.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Biscoito cream cracker', 'Bauducco 200g', 4.69, 'un', 144.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Biscoito cream cracker', 'Bauducco 200g', 4.73, 'un', 31.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Margarina', 'Qualy 500g', 10.30, 'un', 24.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Margarina', 'Qualy 500g', 8.47, 'un', 30.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Margarina', 'Qualy 500g', 9.57, 'un', 23.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Margarina', 'Qualy 500g', 9.11, 'un', 80.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Margarina', 'Qualy 500g', 8.65, 'un', 157.000, '2026-09-01 14:35:00-03'),
        ('Mercado Central do Juazeiro', 'Margarina', 'Doriana 500g', 9.07, 'un', 22.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Margarina', 'Doriana 500g', 7.45, 'un', 22.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Margarina', 'Doriana 500g', 8.42, 'un', 36.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Margarina', 'Doriana 500g', 8.02, 'un', 0.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Margarina', 'Doriana 500g', 7.61, 'un', 170.000, '2026-09-01 14:35:00-03'),
        ('Mercado Central do Juazeiro', 'Ovos de galinha', 'Mantiqueira 12un', 11.57, 'un', 20.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Ovos de galinha', 'Mantiqueira 12un', 13.48, 'un', 35.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Ovos de galinha', 'Mantiqueira 12un', 13.10, 'un', 30.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Ovos de galinha', 'Mantiqueira 12un', 12.47, 'un', 106.000, '2026-09-01 11:20:00-03'),
        ('Supermercado Economia Muriti', 'Ovos de galinha', 'Mantiqueira 12un', 12.61, 'un', 39.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Ovos de galinha', 'Granja Faria 12un', 10.29, 'un', 18.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Ovos de galinha', 'Granja Faria 12un', 11.98, 'un', 27.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Ovos de galinha', 'Granja Faria 12un', 11.65, 'un', 24.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Ovos de galinha', 'Granja Faria 12un', 11.09, 'un', 119.000, '2026-09-01 11:20:00-03'),
        ('Supermercado Economia Muriti', 'Ovos de galinha', 'Granja Faria 12un', 11.21, 'un', 52.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Sabonete', 'Dove 90g', 5.26, 'un', 16.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Sabonete', 'Dove 90g', 5.03, 'un', 40.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Sabonete', 'Dove 90g', 4.35, 'un', 18.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Sabonete', 'Dove 90g', 4.65, 'un', 61.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Sabonete', 'Dove 90g', 4.77, 'un', 88.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Sabonete', 'Dove 90g', 4.10, 'un', 34.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Sabonete', 'Protex 85g', 3.92, 'un', 14.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Sabonete', 'Protex 85g', 3.75, 'un', 32.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Sabonete', 'Protex 85g', 3.24, 'un', 31.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Sabonete', 'Protex 85g', 3.47, 'un', 74.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Sabonete', 'Protex 85g', 3.55, 'un', 101.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Sabonete', 'Protex 85g', 3.05, 'un', 47.000, '2026-09-01 16:05:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Papel higiênico', 'Neve 12 rolos 30m', 26.22, 'un', 24.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Papel higiênico', 'Neve 12 rolos 30m', 22.68, 'un', 25.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Papel higiênico', 'Neve 12 rolos 30m', 20.37, 'un', 87.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Papel higiênico', 'Neve 12 rolos 30m', 24.87, 'un', 114.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Papel higiênico', 'Neve 12 rolos 30m', 20.73, 'un', 60.000, '2026-09-01 16:05:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Papel higiênico', 'Personal 12 rolos 30m', 20.87, 'un', 37.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Papel higiênico', 'Personal 12 rolos 30m', 18.05, 'un', 19.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Papel higiênico', 'Personal 12 rolos 30m', 16.22, 'un', 100.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Papel higiênico', 'Personal 12 rolos 30m', 19.80, 'un', 127.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Papel higiênico', 'Personal 12 rolos 30m', 16.50, 'un', 42.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Detergente líquido', 'Ypê 500ml', 2.80, 'un', 23.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Detergente líquido', 'Ypê 500ml', 2.68, 'un', 29.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Detergente líquido', 'Ypê 500ml', 2.24, 'un', 32.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Detergente líquido', 'Ypê 500ml', 2.48, 'un', 113.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Detergente líquido', 'Ypê 500ml', 2.19, 'un', 140.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Detergente líquido', 'Ypê 500ml', 2.28, 'un', 55.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Detergente líquido', 'Limpol 500ml', 3.14, 'un', 21.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Detergente líquido', 'Limpol 500ml', 3.00, 'un', 21.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Vila Nova Salesianos', 'Detergente líquido', 'Limpol 500ml', 2.50, 'un', 26.000, '2026-09-01 10:00:00-03'),
        ('Hipermercado Lagoa Seca', 'Detergente líquido', 'Limpol 500ml', 2.77, 'un', 55.000, '2026-09-01 11:20:00-03'),
        ('Atacadão do Limoeiro', 'Detergente líquido', 'Limpol 500ml', 2.63, 'un', 153.000, '2026-09-01 14:35:00-03'),
        ('Supermercado Economia Muriti', 'Detergente líquido', 'Limpol 500ml', 2.55, 'un', 37.000, '2026-09-01 16:05:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Carne bovina (patinho)', 'Friboi Patinho 1kg', 37.66, 'kg', 8.000, '2026-09-01 09:05:00-03'),
        ('Hipermercado Lagoa Seca', 'Carne bovina (patinho)', 'Friboi Patinho 1kg', 41.48, 'kg', 14.000, '2026-09-01 11:20:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Carne bovina (patinho)', 'Minerva Patinho 1kg', 34.60, 'kg', 15.000, '2026-09-01 09:05:00-03'),
        ('Hipermercado Lagoa Seca', 'Carne bovina (patinho)', 'Minerva Patinho 1kg', 38.12, 'kg', 21.000, '2026-09-01 11:20:00-03'),
        ('Mercado Central do Juazeiro', 'Banana prata', 'Prata Granel 1kg', 6.25, 'kg', 19.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Banana prata', 'Prata Granel 1kg', 7.28, 'kg', 22.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Economia Muriti', 'Banana prata', 'Prata Granel 1kg', 6.19, 'kg', 8.000, '2026-09-01 16:05:00-03'),
        ('Mercado Central do Juazeiro', 'Banana prata', 'Prata Bandeja 1kg', 7.53, 'kg', 26.000, '2026-09-01 08:10:00-03'),
        ('Supermercado Bom Preço Triângulo', 'Banana prata', 'Prata Bandeja 1kg', 8.77, 'kg', 29.000, '2026-09-01 09:05:00-03'),
        ('Supermercado Economia Muriti', 'Banana prata', 'Prata Bandeja 1kg', 7.46, 'kg', 15.000, '2026-09-01 16:05:00-03')
)
INSERT INTO precos (marca_id, mercado_id, preco, unidade, quantidade_disponivel, coletado_em)
SELECT ma.id, me.id, d.preco, d.unidade, d.quantidade_disponivel, d.coletado_em
  FROM dados d
  JOIN mercados me ON me.nome = d.mercado_nome
  JOIN produtos pr ON pr.nome = d.produto_nome
  JOIN marcas   ma ON ma.produto_id = pr.id AND ma.nome = d.marca_nome
 WHERE NOT EXISTS (
       SELECT 1
         FROM precos p
        WHERE p.marca_id   = ma.id
          AND p.mercado_id = me.id
          AND p.coletado_em = d.coletado_em
 );

-- -----------------------------------------------------------------------------
-- 6. Usuário de demonstração
--
-- E-mail: demo@exemplo.com     Senha: demo1234
--
-- O hash abaixo é bcrypt de custo 10, prefixo $2a$, e foi gerado e conferido
-- com a biblioteca `bcrypt` do Python (hashpw + checkpw contra 'demo1234' e
-- contra uma senha errada). É compatível com golang.org/x/crypto/bcrypt.
--
-- Para regerar (por exemplo, ao trocar a senha de demonstração):
--     python -c "import bcrypt; print(bcrypt.hashpw(b'demo1234', bcrypt.gensalt(rounds=10, prefix=b'2a')).decode())"
-- e substituir a string abaixo. Um novo hash é diferente a cada execução (salt
-- aleatório) e continua válido.
--
-- Credencial de PoC, publicada em repositório: NÃO reutilizar em nada real.
-- -----------------------------------------------------------------------------
INSERT INTO usuarios (nome, email, senha_hash)
VALUES ('Usuário de Demonstração', 'demo@exemplo.com',
        '$2a$10$PJANUdEEYg180oCDMcqcw.dDCHbON2gla7TVxZdRwWsanL3kEYMoG')
ON CONFLICT (email) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 7. Listas de compra de exemplo
--
-- "Cesta básica de setembro": os 18 produtos, uma linha cada. Nenhum mercado
-- sozinho a atende, então força a recomendação multi-mercado e exercita a
-- comparação parcial contra o baseline de mercado único.
--
-- "Compra rápida da semana": 6 itens, cesta menor que vários mercados atendem
-- por inteiro — é o cenário em que a conveniência (1 mercado só) tende a
-- vencer o custo quando `peso_conveniencia` é alto.
-- -----------------------------------------------------------------------------
INSERT INTO listas_compra (usuario_id, nome)
SELECT u.id, d.nome
  FROM (
      VALUES
          ('Cesta básica de setembro'),
          ('Compra rápida da semana')
  ) AS d(nome)
  JOIN usuarios u ON u.email = 'demo@exemplo.com'
 WHERE NOT EXISTS (
       SELECT 1
         FROM listas_compra l
        WHERE l.usuario_id = u.id
          AND l.nome = d.nome
 );

-- -----------------------------------------------------------------------------
-- 8. Itens das listas
--
-- `marca` NULL = indiferença de marca (itens_lista.marca_id NULL): o
-- otimizador pode escolher qualquer marca do produto. Os itens com marca
-- NULL estão marcados abaixo.
--
-- Interações propositais com o estoque:
--   * Leite Piracanjuba 1L, 6 un — o Mercado Central só tem 1, então ele é
--     eliminado como candidato desse item pela restrição de estoque.
--   * Café Pilão 500g, 1 un — o Jardim Patrícia está com 0, idem.
--   * Carne bovina (patinho), 2 kg — só 2 mercados ofertam o produto.
-- -----------------------------------------------------------------------------
INSERT INTO itens_lista (lista_id, produto_id, marca_id, quantidade, unidade)
SELECT l.id, p.id, ma.id, d.quantidade, d.unidade
  FROM (
      VALUES
          ('Cesta básica de setembro', 'Arroz', 'Tio João 5kg'::text, 1.000::numeric(12,3), 'un'),
          -- marca indiferente
          ('Cesta básica de setembro', 'Feijão carioca', NULL, 2.000, 'un'),
          ('Cesta básica de setembro', 'Óleo de soja', 'Liza 900ml', 2.000, 'un'),
          ('Cesta básica de setembro', 'Açúcar refinado', 'União 1kg', 2.000, 'un'),
          -- ruptura no Jd. Patrícia
          ('Cesta básica de setembro', 'Café torrado e moído', 'Pilão 500g', 1.000, 'un'),
          -- estoque baixo no Centro
          ('Cesta básica de setembro', 'Leite integral UHT', 'Piracanjuba 1L', 6.000, 'un'),
          ('Cesta básica de setembro', 'Farinha de trigo', 'Dona Benta 1kg', 1.000, 'un'),
          -- marca indiferente
          ('Cesta básica de setembro', 'Macarrão espaguete', NULL, 3.000, 'un'),
          ('Cesta básica de setembro', 'Sal refinado', 'Cisne 1kg', 1.000, 'un'),
          ('Cesta básica de setembro', 'Molho de tomate', 'Quero 340g', 4.000, 'un'),
          ('Cesta básica de setembro', 'Biscoito cream cracker', 'Piraquê 200g', 2.000, 'un'),
          ('Cesta básica de setembro', 'Margarina', 'Qualy 500g', 1.000, 'un'),
          ('Cesta básica de setembro', 'Ovos de galinha', 'Mantiqueira 12un', 1.000, 'un'),
          ('Cesta básica de setembro', 'Sabonete', 'Protex 85g', 4.000, 'un'),
          ('Cesta básica de setembro', 'Papel higiênico', 'Neve 12 rolos 30m', 1.000, 'un'),
          -- marca indiferente
          ('Cesta básica de setembro', 'Detergente líquido', NULL, 3.000, 'un'),
          -- só 2 mercados ofertam
          ('Cesta básica de setembro', 'Carne bovina (patinho)', 'Friboi Patinho 1kg', 2.000, 'kg'),
          -- marca indiferente
          ('Cesta básica de setembro', 'Banana prata', NULL, 2.000, 'kg'),
          ('Compra rápida da semana', 'Arroz', 'Tio João 5kg', 1.000, 'un'),
          -- marca indiferente
          ('Compra rápida da semana', 'Feijão carioca', NULL, 2.000, 'un'),
          ('Compra rápida da semana', 'Óleo de soja', 'Soya 900ml', 2.000, 'un'),
          -- marca indiferente
          ('Compra rápida da semana', 'Café torrado e moído', NULL, 1.000, 'un'),
          ('Compra rápida da semana', 'Leite integral UHT', 'Itambé 1L', 6.000, 'un'),
          ('Compra rápida da semana', 'Papel higiênico', 'Personal 12 rolos 30m', 1.000, 'un')
  ) AS d(lista_nome, produto_nome, marca_nome, quantidade, unidade)
  JOIN usuarios      u  ON u.email = 'demo@exemplo.com'
  JOIN listas_compra l  ON l.usuario_id = u.id AND l.nome = d.lista_nome
  JOIN produtos      p  ON p.nome = d.produto_nome
  LEFT JOIN marcas   ma ON ma.produto_id = p.id AND ma.nome = d.marca_nome
 WHERE NOT EXISTS (
       SELECT 1
         FROM itens_lista il
        WHERE il.lista_id   = l.id
          AND il.produto_id = p.id
 );

-- =============================================================================
-- Conferências rápidas depois de aplicar (executar manualmente, se quiser):
--
--   -- contagens esperadas: 6 mercados, 18 produtos, 36 marcas, 218 preços
--   SELECT (SELECT count(*) FROM mercados) AS mercados,
--          (SELECT count(*) FROM produtos) AS produtos,
--          (SELECT count(*) FROM marcas)   AS marcas,
--          (SELECT count(*) FROM precos)   AS precos,
--          (SELECT count(*) FROM precos_vigentes) AS vigentes;
--
--   -- nenhum mercado é o mais barato em tudo: a contagem deve se espalhar
--   SELECT m.nome, count(*) AS marcas_em_que_e_o_mais_barato
--     FROM precos_vigentes pv
--     JOIN mercados m ON m.id = pv.mercado_id
--    WHERE pv.preco = (SELECT min(pv2.preco)
--                        FROM precos_vigentes pv2
--                       WHERE pv2.marca_id = pv.marca_id)
--    GROUP BY m.nome
--    ORDER BY 2 DESC;
--
--   -- nenhum mercado cobre os 18 produtos
--   SELECT m.nome, count(DISTINCT ma.produto_id) AS produtos_cobertos
--     FROM precos_vigentes pv
--     JOIN mercados m  ON m.id = pv.mercado_id
--     JOIN marcas   ma ON ma.id = pv.marca_id
--    GROUP BY m.nome
--    ORDER BY 2 DESC;
-- =============================================================================
