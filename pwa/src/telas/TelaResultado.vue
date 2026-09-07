<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import SeletorDePerfil from '@/componentes/SeletorDePerfil.vue'
import { useListasStore } from '@/stores/listas'
import { useRecomendacaoStore } from '@/stores/recomendacao'
import {
  explicarMotivo,
  explicarStatus,
  formatarDistancia,
  formatarPercentual,
  formatarQuantidade,
  formatarReais
} from '@/utilitarios/formato'
import type { PerfilConveniencia } from '@/api/tipos'

const props = defineProps<{ id: string }>()

const listas = useListasStore()
const recomendacao = useRecomendacaoStore()

const listaId = computed<number>(() => Number(props.id))
const perfil = ref<PerfilConveniencia>('equilibrado')

onMounted(() => {
  void listas.carregarLista(listaId.value)
})

const resultado = computed(() => recomendacao.atual)

const listaVazia = computed<boolean>(
  () => (listas.listaAtual?.itens.length ?? 0) === 0 && !listas.carregando
)

const economia = computed(() => resultado.value?.economia ?? null)

const temEconomiaCalculada = computed<boolean>(
  () => economia.value !== null && economia.value.economia_centavos !== null
)

async function gerar(): Promise<void> {
  await recomendacao.gerar(listaId.value, { perfil: perfil.value })
}
</script>

<template>
  <section>
    <RouterLink :to="{ name: 'editor-lista', params: { id: listaId } }" class="voltar">
      ← Editar lista
    </RouterLink>
    <h1>Recomendação</h1>
    <p class="suave">{{ listas.listaAtual?.nome }}</p>

    <div class="cartao">
      <SeletorDePerfil v-model="perfil" />

      <p v-if="listaVazia" class="aviso atencao">
        Esta lista está vazia. Adicione itens antes de gerar a recomendação.
      </p>

      <button
        type="button"
        class="largura-total"
        :disabled="recomendacao.gerando || listaVazia"
        @click="gerar"
      >
        {{ recomendacao.gerando ? 'Calculando a melhor combinação…' : 'Gerar recomendação' }}
      </button>
      <p v-if="recomendacao.gerando" class="suave">
        O sistema está comparando todas as combinações de mercados. Isso leva alguns
        segundos.
      </p>
    </div>

    <p v-if="recomendacao.erro" class="aviso erro" role="alert">{{ recomendacao.erro }}</p>

    <div v-if="resultado" aria-live="polite">
      <div class="cartao resumo">
        <div class="linha-entre">
          <div>
            <p class="suave sem-margem">Custo total estimado</p>
            <p class="destaque">{{ formatarReais(resultado.custo_total_centavos) }}</p>
          </div>
          <span class="etiqueta">{{ explicarStatus(resultado.status) }}</span>
        </div>

        <dl class="indicadores">
          <div>
            <dt>Itens</dt>
            <dd>{{ formatarReais(resultado.custo_itens_centavos) }}</dd>
          </div>
          <div>
            <dt>Deslocamento</dt>
            <dd>{{ formatarReais(resultado.custo_logistico_centavos) }}</dd>
          </div>
          <div>
            <dt>Mercados</dt>
            <dd>{{ resultado.quantidade_mercados_visitados }}</dd>
          </div>
          <div>
            <dt>Distância</dt>
            <dd>{{ formatarDistancia(resultado.distancia_total_km) }}</dd>
          </div>
        </dl>

        <p v-if="resultado.origem_aproximada" class="suave">
          Distância estimada a partir do centro de Juazeiro do Norte, porque você não
          informou um ponto de partida.
        </p>
      </div>

      <div v-if="economia" class="cartao" :class="temEconomiaCalculada ? 'ganho' : ''">
        <h2>Economia estimada</h2>
        <template v-if="temEconomiaCalculada">
          <p class="destaque">
            {{ formatarReais(economia.economia_centavos ?? 0) }}
            <span class="suave">
              ({{ formatarPercentual(economia.economia_percentual ?? 0) }})
            </span>
          </p>
          <p class="suave">
            Comparado a comprar tudo em {{ economia.mercado_unico_nome }}, que sairia por
            {{ formatarReais(economia.custo_mercado_unico_centavos ?? 0) }}.
          </p>
          <p v-if="economia.comparacao_parcial" class="aviso atencao">
            Comparação parcial: nenhum mercado atende sozinho a lista inteira, então só os
            {{ economia.itens_comparados }} itens em comum foram considerados.
          </p>
        </template>
        <p v-else class="suave">{{ economia.observacao }}</p>
      </div>

      <h2>Seu roteiro</h2>
      <p class="suave">Visite os mercados nesta ordem:</p>

      <ol class="roteiro">
        <li v-for="parada in resultado.rota" :key="parada.mercado_id" class="cartao">
          <div class="linha-entre">
            <strong>{{ parada.ordem }}. {{ parada.nome }}</strong>
            <span class="etiqueta">
              {{ formatarDistancia(parada.distancia_do_anterior_km) }}
            </span>
          </div>

          <template
            v-for="compra in resultado.compras_por_mercado.filter(
              (c) => c.mercado_id === parada.mercado_id
            )"
            :key="compra.mercado_id"
          >
            <p class="suave endereco">{{ compra.endereco }}</p>

            <div class="rolagem-horizontal">
              <table>
                <caption class="visualmente-oculto">
                  Itens a comprar em {{ compra.nome }}
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Item</th>
                    <th scope="col" class="numero">Qtd.</th>
                    <th scope="col" class="numero">Valor</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in compra.itens" :key="item.item_id">
                    <td>
                      {{ item.produto_nome }}
                      <span class="suave">{{ item.marca_nome }}</span>
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
                    <td class="numero">{{ formatarReais(compra.subtotal_centavos) }}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </template>
        </li>
      </ol>

      <div v-if="resultado.itens_nao_atendidos.length > 0" class="cartao">
        <h2>Itens que não foi possível incluir</h2>
        <ul class="nao-atendidos">
          <li v-for="item in resultado.itens_nao_atendidos" :key="item.item_id">
            <strong>{{ item.produto_nome }}</strong>
            <span class="suave">{{ explicarMotivo(item.motivo) }}</span>
          </li>
        </ul>
      </div>

      <RouterLink :to="{ name: 'historico', params: { id: listaId } }">
        Ver histórico desta lista
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.voltar {
  display: inline-block;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
  text-decoration: none;
}

.sem-margem {
  margin: 0;
}

.resumo .destaque {
  margin: 0;
}

.ganho {
  background: var(--cor-sucesso-fundo);
  border-color: #bfe0cb;
}

.indicadores {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.6rem;
  margin: 1rem 0 0;
  padding-top: 0.75rem;
  border-top: 1px solid var(--cor-borda);
}

.indicadores dt {
  font-size: 0.8rem;
  color: var(--cor-texto-suave);
}

.indicadores dd {
  margin: 0;
  font-weight: 600;
}

.roteiro {
  list-style: none;
  padding: 0;
  margin: 0 0 1rem;
}

.endereco {
  margin: 0.25rem 0 0.5rem;
}

.nao-atendidos {
  list-style: none;
  padding: 0;
  margin: 0;
}

.nao-atendidos li {
  display: flex;
  flex-direction: column;
  padding: 0.4rem 0;
  border-bottom: 1px solid var(--cor-borda);
}

.visualmente-oculto {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

@media (min-width: 480px) {
  .indicadores {
    grid-template-columns: repeat(4, 1fr);
  }
}
</style>
