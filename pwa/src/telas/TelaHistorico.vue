<script setup lang="ts">
import { computed, onMounted } from 'vue'
import EstadoDaTela from '@/componentes/EstadoDaTela.vue'
import { useRecomendacaoStore } from '@/stores/recomendacao'
import { formatarDataHora, formatarReais } from '@/utilitarios/formato'

const props = defineProps<{ id: string }>()

const recomendacao = useRecomendacaoStore()
const listaId = computed<number>(() => Number(props.id))

onMounted(() => {
  void recomendacao.carregarHistorico(listaId.value)
})

const rotuloDePerfil: Record<string, string> = {
  economico: 'Econômico',
  equilibrado: 'Equilibrado',
  conveniente: 'Conveniente'
}

/**
 * Reabrir do histórico apenas lê o resultado gravado quando a recomendação foi gerada.
 * Nada é recalculado, o que permite comparar execuções na avaliação de acurácia.
 */
async function abrir(recomendacaoId: number): Promise<void> {
  await recomendacao.abrir(recomendacaoId)
}
</script>

<template>
  <section>
    <RouterLink :to="{ name: 'resultado', params: { id: listaId } }" class="voltar">
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
      Recomendação
    </RouterLink>

    <div class="cabecalho-tela">
      <h1>Histórico</h1>
      <p>
        Cada recomendação é guardada como foi gerada. Reabrir não recalcula nada, o que
        permite comparar perfis e coletas de preço diferentes.
      </p>
    </div>

    <EstadoDaTela
      :carregando="recomendacao.carregando"
      :erro="recomendacao.erro"
      :vazio="recomendacao.historico.length === 0"
      mensagem-carregando="Carregando o histórico…"
      mensagem-vazio="Nenhuma recomendação foi gerada para esta lista ainda."
      @tentar-novamente="recomendacao.carregarHistorico(listaId)"
    >
      <ul class="colecao">
        <li v-for="item in recomendacao.historico" :key="item.id" class="cartao registro">
          <div class="linha-entre">
            <div class="crescer">
              <strong class="valor">{{ formatarReais(item.custo_total_centavos) }}</strong>
              <p class="mini dados">
                <span v-if="item.perfil" class="selo selo--marca">
                  {{ rotuloDePerfil[item.perfil] ?? item.perfil }}
                </span>
                <span v-else-if="item.peso_conveniencia !== undefined" class="selo">
                  peso {{ item.peso_conveniencia }}
                </span>
                {{ formatarDataHora(item.gerado_em) }}
              </p>
            </div>
            <button type="button" class="botao botao--secundario botao--pequeno" @click="abrir(item.id)">
              Abrir
            </button>
          </div>
        </li>
      </ul>
    </EstadoDaTela>

    <div v-if="recomendacao.recomendacaoAberta" class="cartao cartao--marca" aria-live="polite">
      <h2>Recomendação #{{ recomendacao.recomendacaoAberta.id }}</h2>
      <p class="mini">
        Gerada em {{ formatarDataHora(recomendacao.recomendacaoAberta.gerado_em) }} ·
        {{ recomendacao.recomendacaoAberta.quantidade_mercados_visitados }} mercado(s) ·
        {{ formatarReais(recomendacao.recomendacaoAberta.custo_total_centavos) }}
      </p>

      <ol class="resumo-rota">
        <li
          v-for="compra in recomendacao.recomendacaoAberta.compras_por_mercado"
          :key="compra.mercado_id"
        >
          <strong>{{ compra.nome }}</strong>
          <span class="mini">
            {{ compra.itens.length }} item(ns) ·
            {{ formatarReais(compra.subtotal_centavos) }}
          </span>
        </li>
      </ol>
    </div>
  </section>
</template>

<style scoped>
.voltar svg {
  width: 16px;
  height: 16px;
}

.registro {
  padding: var(--esp-3) var(--esp-4);
}

.registro .valor {
  font-size: var(--fonte-media);
}

.dados {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--esp-2);
  margin: var(--esp-1) 0 0;
}

.resumo-rota {
  list-style: none;
  padding: 0;
  margin: 0;
}

.resumo-rota li {
  display: flex;
  flex-direction: column;
  padding: var(--esp-2) 0;
  border-bottom: 1px solid var(--cor-marca-borda);
}

.resumo-rota li:last-child {
  border-bottom: none;
}
</style>
