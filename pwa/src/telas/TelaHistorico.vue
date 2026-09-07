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
      ← Recomendação
    </RouterLink>
    <h1>Histórico</h1>
    <p class="suave">
      Cada recomendação é guardada como foi gerada. Reabrir não recalcula nada, o que
      permite comparar perfis e coletas de preço diferentes.
    </p>

    <EstadoDaTela
      :carregando="recomendacao.carregando"
      :erro="recomendacao.erro"
      :vazio="recomendacao.historico.length === 0"
      mensagem-carregando="Carregando o histórico…"
      mensagem-vazio="Nenhuma recomendação foi gerada para esta lista ainda."
      @tentar-novamente="recomendacao.carregarHistorico(listaId)"
    >
      <ul class="colecao">
        <li v-for="item in recomendacao.historico" :key="item.id" class="cartao">
          <div class="linha-entre">
            <div>
              <strong>{{ formatarReais(item.custo_total_centavos) }}</strong>
              <p class="suave sem-margem">
                {{ formatarDataHora(item.gerado_em) }}
                <template v-if="item.perfil">
                  · {{ rotuloDePerfil[item.perfil] ?? item.perfil }}
                </template>
                <template v-else-if="item.peso_conveniencia !== undefined">
                  · peso {{ item.peso_conveniencia }}
                </template>
              </p>
            </div>
            <button type="button" class="secundario" @click="abrir(item.id)">Abrir</button>
          </div>
        </li>
      </ul>
    </EstadoDaTela>

    <div v-if="recomendacao.atual" class="cartao" aria-live="polite">
      <h2>Recomendação #{{ recomendacao.atual.id }}</h2>
      <p class="suave">
        Gerada em {{ formatarDataHora(recomendacao.atual.gerado_em) }} ·
        {{ recomendacao.atual.quantidade_mercados_visitados }} mercado(s) ·
        {{ formatarReais(recomendacao.atual.custo_total_centavos) }}
      </p>

      <ol class="resumo-rota">
        <li v-for="compra in recomendacao.atual.compras_por_mercado" :key="compra.mercado_id">
          <strong>{{ compra.nome }}</strong>
          <span class="suave">
            {{ compra.itens.length }} item(ns) ·
            {{ formatarReais(compra.subtotal_centavos) }}
          </span>
        </li>
      </ol>
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

.colecao,
.resumo-rota {
  list-style: none;
  padding: 0;
  margin: 0;
}

.resumo-rota li {
  display: flex;
  flex-direction: column;
  padding: 0.4rem 0;
  border-bottom: 1px solid var(--cor-borda);
}

.sem-margem {
  margin: 0.15rem 0 0;
}
</style>
