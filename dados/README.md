# Coleta de preços

Planilhas da coleta manual em Juazeiro do Norte e o conversor que as transforma em SQL.
O protocolo completo está em [`../docs/dados-e-coleta.md`](../docs/dados-e-coleta.md).

```
dados/
├── coleta/
│   ├── modelo_coleta.csv          # planilha em branco, com duas linhas de exemplo
│   └── coleta_2026-09-01.csv      # exemplo de uma rodada preenchida
└── gerar_insercoes.py             # CSV -> SQL (só biblioteca padrão)
```

## Rotina semanal

**1. Copie a planilha em branco** com a data da coleta:

```bash
cp dados/coleta/modelo_coleta.csv dados/coleta/coleta_2026-09-08.csv
```

**2. Preencha uma linha por (mercado, marca).** Colunas:

```
mercado,produto,marca,preco,unidade,quantidade_disponivel,coletado_em
```

Produto em falta entra com `quantidade_disponivel` igual a `0` — **não** omita a linha.
Os nomes precisam bater exatamente com os cadastrados no banco.

**3. Valide antes de gerar qualquer coisa:**

```bash
python dados/gerar_insercoes.py --entrada dados/coleta/coleta_2026-09-08.csv --verificar
```

Cada problema é reportado com a linha e a coluna. O comando sai com código 1 se houver
erro.

**4. Gere o SQL:**

```bash
python dados/gerar_insercoes.py --entrada dados/coleta/coleta_2026-09-08.csv --saida coleta.sql
```

**5. Revise e aplique.** O script nunca escreve no banco; a revisão é o que impede uma
coleta com erro em massa de entrar na série histórica.

```bash
psql "$BANCO_URL" -f coleta.sql
```

**6. Confira** que o número de linhas inseridas bate com o número de linhas do CSV. Como
as chaves estrangeiras são resolvidas por nome, um nome divergente gera um comando válido
que não insere nada.

## Observações

- `precos` é **append-only**: cada coleta acrescenta snapshots e nada é sobrescrito. A
  view `precos_vigentes` seleciona automaticamente o mais recente de cada par
  (marca, mercado).
- Corrigir um preço errado é um novo INSERT com data posterior, nunca um UPDATE.
- Cada INSERT gerado tem `WHERE NOT EXISTS`: aplicar o mesmo arquivo duas vezes não
  duplica observações.
- Unidades aceitas: `kg`, `g`, `L`, `ml`, `un`.
