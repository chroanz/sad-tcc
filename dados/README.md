# Dados

O catálogo da PoC vem da base da cesta básica do DIEESE (`cesta_agosto.csv`, na raiz do
projeto). Não há coleta de preços em supermercados. As regras de conversão estão em
[`../docs/dados-e-coleta.md`](../docs/dados-e-coleta.md).

```
dados/
└── gerar_catalogo_dieese.py   # CSV do DIEESE -> migration SQL (só biblioteca padrão)
```

## Regerar o catálogo

```bash
python3 dados/gerar_catalogo_dieese.py --entrada cesta_agosto.csv \
    --saida api/migracoes/004_catalogo_dieese.sql
```

O script nunca escreve no banco: ele gera o SQL, que a API aplica como migration na subida.

## Observações

- Cada nome de cidade do CSV vira um supermercado fictício em Juazeiro do Norte, com os
  preços DIEESE daquela cidade e localização fictícia num raio de 6 km do centro; os
  produtos são os 13 da cesta; cada produto tem duas marcas fictícias (±8% do preço DIEESE).
- Célula `-` = produto indisponível no supermercado daquela cidade: nenhum preço é inserido.
- Uma migration já aplicada **nunca é reaplicada**. Para carregar uma pesquisa de outro mês
  num banco existente, gere uma migration nova (`005_...`). Num banco de desenvolvimento,
  também dá para recriar o volume com `docker compose down -v`.
- `precos` é **append-only**: um mês novo entra como novos snapshots, com `coletado_em`
  posterior, e a view `precos_vigentes` passa a usá-los automaticamente.
