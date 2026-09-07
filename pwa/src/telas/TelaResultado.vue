<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import SeletorDePerfil from '@/componentes/SeletorDePerfil.vue'
import { useListasStore } from '@/stores/listas'
import { PERFIS, useRecomendacaoStore } from '@/stores/recomendacao'
import { compararPerfis, type ComparacaoDePerfis } from '@/utilitarios/comparacao'
import {
  explicarMotivo,
  explicarStatus,
  formatarDataHora,
  formatarDistancia,
  formatarPercentual,
  formatarQuantidade,
  formatarReais
} from '@/utilitarios/formato'
import type { CompraNoMercado, PerfilConveniencia } from '@/api/tipos'

const props = defineProps<{ id: string }>()

const listas = useListasStore()
const recomendacao = useRecomendacaoStore()

const listaId = computed<number>(() => Number(props.id))

const resultado = computed(() => recomendacao.selecionada)
const economia = computed(() => resultado.value?.economia ?? null)

const listaVazia = computed<boolean>(
  () => (listas.listaAtual?.itens.length ?? 0) === 0 && !listas.carregando
)

const temEconomiaCalculada = computed<boolean>(
  () => economia.value !== null && economia.value.economia_centavos !== null
)

const ROTULOS_DE_PERFIL: Record<PerfilConveniencia, string> = {
  economico: 'Econômico',
  equilibrado: 'Equilibrado',
  conveniente: 'Conveniente'
}

interface Alternativa {
  perfil: PerfilConveniencia
  titulo: string
  comparacao: ComparacaoDePerfis
}

/**
 * Os outros perfis, medidos contra o escolhido. É aqui que a recomendação deixa de ser um
 * veredito e passa a ser um argumento que o usuário pode conferir.
 */
const alternativas = computed<Alternativa[]>(() => {
  const referencia = resultado.value
  if (referencia === null) return []

  return PERFIS.filter((perfil) => perfil !== recomendacao.perfilSelecionado)
    .map((perfil) => {
      const candidato = recomendacao.resultadosPorPerfil[perfil]
      if (candidato === null) return null
      return {
        perfil,
        titulo: ROTULOS_DE_PERFIL[perfil],
        comparacao: compararPerfis(referencia, candidato)
      }
    })
    .filter((alternativa): alternativa is Alternativa => alternativa !== null)
})

/**
 * Os parâmetros que produziram o custo logístico. Recomendações gravadas antes de o
 * contrato ecoá-los chegam sem os campos, e aí a linha simplesmente não aparece.
 */
const parametrosLogisticos = computed<string | null>(() => {
  const porVisita = resultado.value?.custo_por_visita_centavos
  const porKm = resultado.value?.custo_por_km_centavos
  if (!porVisita || !porKm) return null
  return `${formatarReais(porVisita)} por parada e ${formatarReais(porKm)} por quilômetro`
})

/**
 * Compras indexadas por mercado: a rota e as compras chegam em listas separadas, e cruzá-las
 * uma vez aqui evita repetir a varredura a cada parada renderizada.
 */
const comprasPorMercado = computed<Map<number, CompraNoMercado>>(
  () =>
    new Map(
      (resultado.value?.compras_por_mercado ?? []).map((compra) => [compra.mercado_id, compra])
    )
)

/**
 * Chegar nesta tela já é o pedido de recomendação — o botão que trouxe o usuário até aqui
 * dizia "Gerar recomendação", então o cálculo acontece na chegada em vez de exigir um
 * segundo clique com o mesmo rótulo.
 */
onMounted(async () => {
  recomendacao.focarLista(listaId.value)
  await listas.carregarLista(listaId.value)
  if (!listaVazia.value && !recomendacao.temResultados) {
    await recomendacao.gerarTodosOsPerfis(listaId.value)
  }
})

watch(listaId, async (novoId) => {
  recomendacao.focarLista(novoId)
  await listas.carregarLista(novoId)
  if (!listaVazia.value) await recomendacao.gerarTodosOsPerfis(novoId)
})

async function recalcular(): Promise<void> {
  await recomendacao.gerarTodosOsPerfis(listaId.value)
}
</script>

<template>
  <section>
    <RouterLink :to="{ name: 'editor-lista', params: { id: listaId } }" class="voltar">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M15 6l-6 6 6 6" />
      </svg>
      Editar lista
    </RouterLink>

    <div class="cabecalho-tela">
      <h1>Sua recomendação</h1>
      <p>{{ listas.listaAtual?.nome }}</p>
    </div>

    <p v-if="listaVazia" class="aviso aviso--atencao">
      Esta lista está vazia. Adicione itens antes de gerar a recomendação.
    </p>

    <div v-if="recomendacao.gerando" role="status" aria-live="polite">
      <span class="oculto-visual">Comparando os três perfis de compra</span>
      <div class="cartao" aria-hidden="true">
        <div class="esqueleto esqueleto--titulo"></div>
        <div class="esqueleto esqueleto--linha"></div>
        <div class="esqueleto esqueleto--linha esqueleto--curta"></div>
      </div>
    </div>

    <p v-if="recomendacao.erro" class="aviso aviso--erro" role="alert">
      {{ recomendacao.erro }}
    </p>

    <div v-if="resultado" aria-live="polite">
      <div class="cartao">
        <SeletorDePerfil
          v-model="recomendacao.perfilSelecionado"
          :resultados="recomendacao.resultadosPorPerfil"
        />
      </div>

      <!-- A resposta que o usuário veio buscar: quanto sai do bolso e quanto se anda. -->
      <div class="cartao resposta">
        <p class="rotulo">Você paga nos mercados</p>
        <p class="valor valor--grande">
          {{ formatarReais(resultado.custo_itens_centavos) }}
        </p>
        <p class="linha resumo-rota">
          <span class="selo selo--marca">
            {{ resultado.quantidade_mercados_visitados }} mercado(s)
          </span>
          <span class="selo">{{ formatarDistancia(resultado.distancia_total_km) }}</span>
        </p>

      </div>

      <!--
        O sistema não sabe quanto vale um quilômetro para quem vai comprar: o custo por km
        é parâmetro de servidor, calibrado para carro. Em vez de impor esse valor, mostra
        o limiar em que a escolha se inverte e devolve o julgamento ao usuário.
      -->
      <div v-if="alternativas.length > 0" class="cartao">
        <h2>Por que este perfil?</h2>
        <ul class="alternativas">
          <li v-for="alternativa in alternativas" :key="alternativa.perfil">
            <strong>{{ alternativa.titulo }}</strong>
            <span class="mini">{{ alternativa.comparacao.resumo }}</span>
            <span v-if="alternativa.comparacao.pontoDeEquilibrio" class="limiar">
              {{ alternativa.comparacao.pontoDeEquilibrio }}
            </span>
          </li>
        </ul>
      </div>

      <!-- Antes do roteiro: faltar item muda a decisão de compra inteira. -->
      <div
        v-if="resultado.itens_nao_atendidos.length > 0"
        class="cartao cartao--destaque"
      >
        <h2>{{ resultado.itens_nao_atendidos.length }} item(ns) fora da recomendação</h2>
        <ul class="nao-atendidos">
          <li v-for="item in resultado.itens_nao_atendidos" :key="item.item_id">
            <strong>{{ item.produto_nome }}</strong>
            <span class="mini">{{ explicarMotivo(item.motivo) }}</span>
          </li>
        </ul>
        <RouterLink
          :to="{ name: 'editor-lista', params: { id: listaId } }"
          class="botao botao--secundario botao--pequeno"
        >
          Ajustar a lista
        </RouterLink>
      </div>

      <div v-if="economia" class="cartao" :class="temEconomiaCalculada ? 'cartao--marca' : ''">
        <h2>Economia estimada</h2>
        <template v-if="temEconomiaCalculada">
          <p class="valor economia-valor">
            {{ formatarReais(economia.economia_centavos ?? 0) }}
            <span class="mini">
              ({{ formatarPercentual(economia.economia_percentual ?? 0) }})
            </span>
          </p>
          <p class="mini">
            Comparado a comprar tudo em {{ economia.mercado_unico_nome }}, considerando o
            deslocamento dos dois lados com a mesma régua.
          </p>
          <p v-if="economia.comparacao_parcial" class="aviso aviso--atencao">
            Comparação parcial: nenhum mercado atende sozinho a lista inteira, então só os
            {{ economia.itens_comparados }} itens em comum foram considerados.
          </p>
        </template>
        <p v-else class="mini">{{ economia.observacao }}</p>
      </div>

      <h2>Seu roteiro</h2>
      <p class="mini roteiro-nota">Visite os mercados nesta ordem:</p>

      <ol class="roteiro">
        <li v-for="parada in resultado.rota" :key="parada.mercado_id" class="parada">
          <span class="parada__marca" aria-hidden="true">{{ parada.ordem }}</span>

          <div class="cartao parada__cartao">
            <div class="linha-entre">
              <strong>{{ parada.nome }}</strong>
              <span class="selo">
                {{ formatarDistancia(parada.distancia_do_anterior_km) }}
              </span>
            </div>

            <template v-if="comprasPorMercado.get(parada.mercado_id)">
              <p class="mini endereco">
                {{ comprasPorMercado.get(parada.mercado_id)?.endereco }}
              </p>

              <div class="rolagem-horizontal">
                <table>
                  <caption class="oculto-visual">
                    Itens a comprar em {{ parada.nome }}
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">Item</th>
                      <th scope="col" class="numero">Qtd.</th>
                      <th scope="col" class="numero">Valor</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="item in comprasPorMercado.get(parada.mercado_id)?.itens ?? []"
                      :key="item.item_id"
                    >
                      <td>
                        {{ item.produto_nome }}
                        <span class="mini">{{ item.marca_nome }}</span>
                      </td>
                      <td class="numero">
                        {{ formatarQuantidade(item.quantidade, item.unidade) }}
                      </td>
                      <td class="numero">{{ formatarReais(item.custo_centavos) }}</td>
                    </tr>
                  </tbody>
                  <tfoot>
                    <tr>
                      <th scope="row" colspan="2">Subtotal</th>
                      <td class="numero">
                        {{
                          formatarReais(
                            comprasPorMercado.get(parada.mercado_id)?.subtotal_centavos ?? 0
                          )
                        }}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </template>
          </div>
        </li>
      </ol>

      <!-- Vocabulário do solver interessa à avaliação do modelo, não a quem vai comprar. -->
      <details class="cartao tecnico">
        <summary>Detalhes técnicos desta recomendação</summary>
        <dl>
          <div>
            <dt>Deslocamento estimado</dt>
            <dd>{{ formatarReais(resultado.custo_logistico_centavos) }}</dd>
          </div>
          <div>
            <dt>Custo considerado na decisão</dt>
            <dd>{{ formatarReais(resultado.custo_total_centavos) }}</dd>
          </div>
          <div v-if="parametrosLogisticos">
            <dt>Parâmetros do deslocamento</dt>
            <dd>{{ parametrosLogisticos }}</dd>
          </div>
          <div>
            <dt>Status do solver</dt>
            <dd>{{ explicarStatus(resultado.status) }}</dd>
          </div>
          <div>
            <dt>Peso de conveniência</dt>
            <dd>{{ resultado.peso_conveniencia }}</dd>
          </div>
          <div>
            <dt>Gerada em</dt>
            <dd>{{ formatarDataHora(resultado.gerado_em) }}</dd>
          </div>
          <div>
            <dt>Ponto de partida</dt>
            <dd>
              {{
                resultado.origem_aproximada
                  ? 'Centro de Juazeiro do Norte (aproximado)'
                  : 'Origem informada'
              }}
            </dd>
          </div>
        </dl>
        <p class="mini nota-tecnica">
          O deslocamento não é pago no supermercado: é a estimativa que torna comparáveis
          preço e conveniência dentro do modelo.
        </p>
      </details>

      <RouterLink
        :to="{ name: 'historico', params: { id: listaId } }"
        class="botao botao--fantasma botao--bloco"
      >
        Ver histórico desta lista
      </RouterLink>

      <div class="barra-acao">
        <div class="barra-acao__interno">
          <span class="barra-acao__resumo">
            <span class="barra-acao__rotulo">Você paga</span>
            <span class="barra-acao__valor">
              {{ formatarReais(resultado.custo_itens_centavos) }}
            </span>
          </span>
          <button
            type="button"
            class="botao botao--secundario"
            :disabled="recomendacao.gerando"
            @click="recalcular"
          >
            {{ recomendacao.gerando ? 'Recalculando…' : 'Recalcular' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.voltar svg {
  width: 16px;
  height: 16px;
}

.resposta .rotulo {
  margin: 0;
}

.resposta .valor--grande {
  margin: var(--esp-1) 0 var(--esp-3);
  color: var(--cor-marca-forte);
}

.resumo-rota {
  margin: 0;
}

.alternativas {
  list-style: none;
  padding: 0;
  margin: 0;
}

.alternativas li {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--esp-3) 0;
  border-bottom: 1px solid var(--cor-borda);
}

.alternativas li:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

/* O limiar é a informação que devolve a decisão ao usuário: ganha peso e cor de marca. */
.limiar {
  margin-top: var(--esp-1);
  font-size: var(--fonte-pequena);
  font-weight: var(--peso-medio);
  color: var(--cor-marca-forte);
}

.economia-valor {
  margin: 0 0 var(--esp-2);
  font-size: var(--fonte-grande);
  color: var(--cor-marca-forte);
}

.nao-atendidos {
  list-style: none;
  padding: 0;
  margin: 0 0 var(--esp-3);
}

.nao-atendidos li {
  display: flex;
  flex-direction: column;
  padding: var(--esp-2) 0;
  border-bottom: 1px solid var(--cor-destaque-borda);
}

.roteiro-nota {
  margin-bottom: var(--esp-3);
}

.roteiro {
  list-style: none;
  padding: 0;
  margin: 0 0 var(--esp-4);
}

/* Linha do tempo: as paradas se leem como etapas de um percurso, não como cartões soltos. */
.parada {
  position: relative;
  display: flex;
  gap: var(--esp-3);
}

.parada__marca {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  margin-top: var(--esp-4);
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--cor-marca);
  color: var(--cor-texto-inverso);
  font-size: var(--fonte-pequena);
  font-weight: var(--peso-extra);
}

.parada:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 15px;
  top: calc(var(--esp-4) + 32px);
  bottom: 0;
  width: 2px;
  background: var(--cor-marca-borda);
}

.parada__cartao {
  flex: 1;
  min-width: 0;
}

.endereco {
  margin: var(--esp-1) 0 var(--esp-3);
}

.tecnico summary {
  cursor: pointer;
  min-height: var(--alvo-toque);
  display: flex;
  align-items: center;
  font-size: var(--fonte-pequena);
  font-weight: var(--peso-medio);
  color: var(--cor-texto-suave);
}

.tecnico dl {
  margin: var(--esp-2) 0 0;
  display: grid;
  gap: var(--esp-2);
}

.tecnico dl > div {
  display: flex;
  justify-content: space-between;
  gap: var(--esp-3);
  font-size: var(--fonte-pequena);
}

.tecnico dt {
  color: var(--cor-texto-suave);
}

.tecnico dd {
  margin: 0;
  text-align: right;
}

.nota-tecnica {
  margin: var(--esp-3) 0 0;
}
</style>
