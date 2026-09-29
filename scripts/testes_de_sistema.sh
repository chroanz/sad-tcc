#!/usr/bin/env bash
# Testes de sistema ponta a ponta contra a pilha em execucao.
#
# Executa os cenarios descritos em docs/plano-de-testes.md (S01-S18 e B01-B13)
# contra a API real, com banco e otimizador de pe. Sai com codigo 1 se algum
# cenario falhar, para servir de portao de qualidade.
#
# Pre-requisito:  docker compose up -d --build
# Uso:            bash scripts/testes_de_sistema.sh

set -uo pipefail

BASE="${BASE_API:-http://localhost:8080}"
API="$BASE/api/v1"

total=0
falhas=0

verde()   { printf '\033[32m%s\033[0m\n' "$1"; }
vermelho(){ printf '\033[31m%s\033[0m\n' "$1"; }

# checar <id> <descricao> <esperado> <obtido>
checar() {
  total=$((total + 1))
  if [ "$3" = "$4" ]; then
    verde "  [OK]    $1  $2"
  else
    falhas=$((falhas + 1))
    vermelho "  [FALHA] $1  $2"
    vermelho "          esperado: $3"
    vermelho "          obtido:   $4"
  fi
}

# checar_verdadeiro <id> <descricao> <condicao ja avaliada: 0/1>
checar_verdadeiro() {
  total=$((total + 1))
  if [ "$3" = "1" ]; then
    verde "  [OK]    $1  $2"
  else
    falhas=$((falhas + 1))
    vermelho "  [FALHA] $1  $2"
  fi
}

# extrai um caminho pontilhado de um JSON vindo da entrada padrao
extrair() {
  python3 -c '
import sys, json

try:
    dados = json.load(sys.stdin)
except Exception:
    print("")
    sys.exit(0)

for parte in sys.argv[1].split("."):
    if parte == "":
        continue
    try:
        if isinstance(dados, list):
            dados = dados[int(parte)]
        else:
            dados = dados.get(parte)
    except Exception:
        dados = None
    if dados is None:
        break

if dados is None:
    print("")
elif isinstance(dados, bool):
    print("true" if dados else "false")
elif isinstance(dados, (dict, list)):
    print(json.dumps(dados, sort_keys=True, ensure_ascii=False))
else:
    print(dados)
' "$1"
}

# status_de <metodo> <url> [corpo] [token]
status_de() {
  if [ -n "${3:-}" ]; then
    curl -s -o /dev/null -w '%{http_code}' -X "$1" "$2" \
      -H 'Content-Type: application/json' \
      ${4:+-H "Authorization: Bearer $4"} -d "$3"
  else
    curl -s -o /dev/null -w '%{http_code}' -X "$1" "$2" ${4:+-H "Authorization: Bearer $4"}
  fi
}

echo
echo "== Testes de sistema =="
echo "Base: $BASE"
echo

# ---------------------------------------------------------------- S01 saude
echo "-- Infraestrutura"
saude=$(curl -s "$BASE/saude")
checar "S01a" "saude geral responde ok"        "ok" "$(echo "$saude" | extrair status)"
checar "S01b" "banco acessivel"                "ok" "$(echo "$saude" | extrair banco)"
checar "S01c" "otimizador acessivel"           "ok" "$(echo "$saude" | extrair otimizador)"

# ---------------------------------------------------------------- S03 login
echo
echo "-- Autenticacao"
login=$(curl -s -X POST "$API/auth/entrar" -H 'Content-Type: application/json' \
  -d '{"email":"demo@exemplo.com","senha":"demo1234"}')
TOKEN=$(echo "$login" | extrair token)
checar_verdadeiro "S03" "login do usuario de demonstracao" "$([ -n "$TOKEN" ] && echo 1 || echo 0)"

if [ -z "$TOKEN" ]; then
  vermelho "Sem token; os demais cenarios nao podem rodar."
  exit 1
fi

checar "B11" "e-mail duplicado devolve 409" "409" \
  "$(status_de POST "$API/auth/registrar" '{"nome":"Outro","email":"demo@exemplo.com","senha":"segredo123"}')"

checar "B09" "token invalido devolve 401" "401" \
  "$(curl -s -o /dev/null -w '%{http_code}' "$API/listas" -H 'Authorization: Bearer token-falso')"

# ---------------------------------------------------------------- S04 listas
echo
echo "-- Catalogo e listas da semente"
listas=$(curl -s "$API/listas" -H "Authorization: Bearer $TOKEN")
qtd_listas=$(echo "$listas" | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))')
checar_verdadeiro "S04" "usuario demo tem ao menos 1 lista ($qtd_listas)" \
  "$([ "$qtd_listas" -ge 1 ] && echo 1 || echo 0)"

mercados=$(curl -s "$API/mercados" -H "Authorization: Bearer $TOKEN")
qtd_mercados=$(echo "$mercados" | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))')
checar "S02a" "28 supermercados (um por cidade do CSV DIEESE) no catalogo" "28" "$qtd_mercados"

produtos=$(curl -s "$API/produtos" -H "Authorization: Bearer $TOKEN")
qtd_produtos=$(echo "$produtos" | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))')
checar "S02b" "13 produtos da cesta DIEESE no catalogo" "13" "$qtd_produtos"

LISTA_ID=$(echo "$listas" | python3 -c '
import sys, json
listas = json.load(sys.stdin)
maior = max(listas, key=lambda l: l.get("quantidade_itens") or 0)
print(maior["id"])
')
echo "  (usando a lista $LISTA_ID nos cenarios de recomendacao)"

# ------------------------------------------------------- S05 recomendacao
echo
echo "-- Recomendacao"
rec=$(curl -s -X POST "$API/listas/$LISTA_ID/recomendacoes" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"perfil":"equilibrado"}')
REC_ID=$(echo "$rec" | extrair id)
checar "S05a" "status do solver" "OTIMO" "$(echo "$rec" | extrair status)"
checar_verdadeiro "S05b" "rota nao vazia" \
  "$(echo "$rec" | python3 -c 'import sys,json; print(1 if json.load(sys.stdin).get("rota") else 0)')"
checar_verdadeiro "S05c" "custo total positivo" \
  "$(echo "$rec" | python3 -c 'import sys,json; print(1 if json.load(sys.stdin).get("custo_total_centavos",0)>0 else 0)')"
checar_verdadeiro "S05d" "custo total = itens + logistica" \
  "$(echo "$rec" | python3 -c '
import sys, json
d = json.load(sys.stdin)
print(1 if d["custo_total_centavos"] == d["custo_itens_centavos"] + d["custo_logistico_centavos"] else 0)')"

checar "B12" "origem omitida marca distancia como aproximada" "true" \
  "$(echo "$rec" | extrair origem_aproximada)"

# ------------------------------------------------------- S06/S07 historico
historico=$(curl -s "$API/listas/$LISTA_ID/recomendacoes" -H "Authorization: Bearer $TOKEN")
checar_verdadeiro "S06" "recomendacao aparece no historico" \
  "$(echo "$historico" | python3 -c "
import sys, json
print(1 if any(str(r['id']) == '$REC_ID' for r in json.load(sys.stdin)) else 0)")"

primeira=$(curl -s "$API/recomendacoes/$REC_ID" -H "Authorization: Bearer $TOKEN" | extrair compras_por_mercado)
segunda=$(curl -s "$API/recomendacoes/$REC_ID" -H "Authorization: Bearer $TOKEN" | extrair compras_por_mercado)
checar "S07" "reabrir do historico nao recalcula" "$primeira" "$segunda"

# --------------------------------------------------- S09/S10 os tres perfis
echo
echo "-- Trade-off custo x conveniencia"
gerar_perfil() {
  curl -s -X POST "$API/listas/$LISTA_ID/recomendacoes" \
    -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
    -d "{\"perfil\":\"$1\"}"
}

eco=$(gerar_perfil economico)
equ=$(gerar_perfil equilibrado)
con=$(gerar_perfil conveniente)

m_eco=$(echo "$eco" | extrair quantidade_mercados_visitados)
m_equ=$(echo "$equ" | extrair quantidade_mercados_visitados)
m_con=$(echo "$con" | extrair quantidade_mercados_visitados)
i_eco=$(echo "$eco" | extrair custo_itens_centavos)
i_con=$(echo "$con" | extrair custo_itens_centavos)

echo "  economico:   $m_eco mercado(s), itens=$i_eco"
echo "  equilibrado: $m_equ mercado(s)"
echo "  conveniente: $m_con mercado(s), itens=$i_con"

checar_verdadeiro "S09a" "economico visita ao menos tantos mercados quanto conveniente" \
  "$([ "$m_eco" -ge "$m_con" ] && echo 1 || echo 0)"
checar_verdadeiro "S09b" "economico gasta em itens no maximo o do conveniente" \
  "$([ "$i_eco" -le "$i_con" ] && echo 1 || echo 0)"
checar_verdadeiro "S10" "numero de mercados nao cresce com o peso" \
  "$([ "$m_eco" -ge "$m_equ" ] && [ "$m_equ" -ge "$m_con" ] && echo 1 || echo 0)"

# ------------------------------------------------------- S11 determinismo
a=$(gerar_perfil equilibrado | extrair compras_por_mercado)
b=$(gerar_perfil equilibrado | extrair compras_por_mercado)
checar "S11" "mesma entrada produz a mesma alocacao" "$a" "$b"

# ------------------------------------------------------------ casos de borda
echo
echo "-- Casos de borda"
vazia=$(curl -s -X POST "$API/listas" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"nome":"Lista vazia de teste"}')
VAZIA_ID=$(echo "$vazia" | extrair id)

rec_vazia=$(curl -s -X POST "$API/listas/$VAZIA_ID/recomendacoes" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"perfil":"equilibrado"}')
checar "B01a" "lista vazia devolve custo zero" "0" \
  "$(echo "$rec_vazia" | extrair custo_total_centavos)"
checar "B01b" "lista vazia nao gera erro" "201" \
  "$(status_de POST "$API/listas/$VAZIA_ID/recomendacoes" '{"perfil":"equilibrado"}' "$TOKEN")"

checar "B10" "unidade invalida devolve 400" "400" \
  "$(status_de POST "$API/listas/$VAZIA_ID/itens" '{"produto_id":1,"quantidade":1,"unidade":"litro"}' "$TOKEN")"

checar "B10b" "quantidade zero devolve 400" "400" \
  "$(status_de POST "$API/listas/$VAZIA_ID/itens" '{"produto_id":1,"quantidade":0,"unidade":"un"}' "$TOKEN")"

checar "VAL" "perfil invalido devolve 400" "400" \
  "$(status_de POST "$API/listas/$VAZIA_ID/recomendacoes" '{"perfil":"barato"}' "$TOKEN")"

# B08: lista de outro usuario
sufixo=$(date +%s)
outro=$(curl -s -X POST "$API/auth/registrar" -H 'Content-Type: application/json' \
  -d "{\"nome\":\"Outro Usuario\",\"email\":\"outro$sufixo@exemplo.com\",\"senha\":\"segredo123\"}")
TOKEN_OUTRO=$(echo "$outro" | extrair token)
checar "B08" "lista de outro usuario devolve 403" "403" \
  "$(curl -s -o /dev/null -w '%{http_code}' "$API/listas/$LISTA_ID" \
     -H "Authorization: Bearer $TOKEN_OUTRO")"

checar "404" "lista inexistente devolve 404" "404" \
  "$(curl -s -o /dev/null -w '%{http_code}' "$API/listas/999999" -H "Authorization: Bearer $TOKEN")"

# B06: teto de 20 itens
teto=$(curl -s -X POST "$API/listas" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"nome":"Lista acima do teto"}')
TETO_ID=$(echo "$teto" | extrair id)
ids_produtos=$(echo "$produtos" | python3 -c 'import sys,json; print(" ".join(str(p["id"]) for p in json.load(sys.stdin)))')
contador=0
for pid in $ids_produtos; do
  curl -s -o /dev/null -X POST "$API/listas/$TETO_ID/itens" \
    -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
    -d "{\"produto_id\":$pid,\"quantidade\":1,\"unidade\":\"un\"}"
  contador=$((contador + 1))
done
# repete produtos ate ultrapassar o teto de 20
for pid in $ids_produtos; do
  [ "$contador" -ge 21 ] && break
  curl -s -o /dev/null -X POST "$API/listas/$TETO_ID/itens" \
    -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
    -d "{\"produto_id\":$pid,\"quantidade\":2,\"unidade\":\"un\"}"
  contador=$((contador + 1))
done
checar "B06" "lista com $contador itens excede o teto e devolve 400" "400" \
  "$(status_de POST "$API/listas/$TETO_ID/recomendacoes" '{"perfil":"equilibrado"}' "$TOKEN")"

# ------------------------------------------------- origem e raio de busca (S13-S16)
echo
echo "-- Origem informada e recorte por raio --"

# Centro de Juazeiro do Norte, o mesmo padrao do servidor. Os supermercados ficam num
# raio de 6 km do centro: 7 km alcancam todos, 3 km so uma parte.
ORIGEM='{"latitude":-7.213100,"longitude":-39.315300}'

com_origem=$(curl -s -X POST "$API/listas/$LISTA_ID/recomendacoes" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"perfil\":\"equilibrado\",\"origem\":$ORIGEM}")

checar "S13" "origem informada deixa de ser aproximada" "false" \
  "$(echo "$com_origem" | extrair origem_aproximada)"

com_raio=$(curl -s -X POST "$API/listas/$LISTA_ID/recomendacoes" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"perfil\":\"equilibrado\",\"origem\":$ORIGEM,\"raio_km\":7}")

checar "S14" "raio amplo devolve o recorte usado" "7" \
  "$(echo "$com_raio" | extrair raio_km)"

mercados_amplo=$(echo "$com_raio" | extrair mercados_considerados)
checar_verdadeiro "S15" "raio amplo considera ao menos 2 mercados ($mercados_amplo)" \
  "$([ "${mercados_amplo:-0}" -ge 2 ] && echo 1 || echo 0)"

# Raio minusculo nao alcanca mercado nenhum: precisa de erro claro, nao de 500.
checar "S16" "raio sem nenhum mercado devolve 400" "400" \
  "$(status_de POST "$API/listas/$LISTA_ID/recomendacoes" \
     "{\"perfil\":\"equilibrado\",\"origem\":$ORIGEM,\"raio_km\":0.01}" "$TOKEN")"

# Regressao: com o recorte ativo, os candidatos precisam ser restritos aos mercados
# selecionados. Sem isso o otimizador recusa o payload inteiro com 422, porque uma oferta
# aponta para um mercado que nao consta da lista.
raio_estreito=$(curl -s -X POST "$API/listas/$LISTA_ID/recomendacoes" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"perfil\":\"equilibrado\",\"origem\":$ORIGEM,\"raio_km\":3}")

checar "S17" "raio que exclui mercados ainda resolve" "OTIMO" \
  "$(echo "$raio_estreito" | extrair status)"

mercados_estreito=$(echo "$raio_estreito" | extrair mercados_considerados)
checar_verdadeiro "S18" \
  "raio estreito considera menos mercados que o amplo ($mercados_estreito < $mercados_amplo)" \
  "$([ "${mercados_estreito:-0}" -lt "${mercados_amplo:-0}" ] && echo 1 || echo 0)"

checar "B13" "raio negativo devolve 400" "400" \
  "$(status_de POST "$API/listas/$LISTA_ID/recomendacoes" \
     "{\"perfil\":\"equilibrado\",\"origem\":$ORIGEM,\"raio_km\":-1}" "$TOKEN")"

# limpeza das listas criadas pelo teste
curl -s -o /dev/null -X DELETE "$API/listas/$VAZIA_ID" -H "Authorization: Bearer $TOKEN"
curl -s -o /dev/null -X DELETE "$API/listas/$TETO_ID" -H "Authorization: Bearer $TOKEN"

# ------------------------------------------------------------------ resumo
echo
echo "== Resumo =="
if [ "$falhas" -eq 0 ]; then
  verde "$total cenario(s), 0 falha(s)."
  exit 0
fi
vermelho "$total cenario(s), $falhas falha(s)."
exit 1
