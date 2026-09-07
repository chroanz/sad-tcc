<script setup lang="ts">
import { onMounted } from 'vue'
import EstadoDaTela from '@/componentes/EstadoDaTela.vue'
import { useCatalogoStore } from '@/stores/catalogo'
import { formatarCoordenada } from '@/utilitarios/formato'

const catalogo = useCatalogoStore()

onMounted(() => {
  void catalogo.carregarMercados()
})
</script>

<template>
  <section>
    <h1>Mercados</h1>
    <p class="suave">
      Supermercados considerados nas recomendações. O recorte do trabalho é Juazeiro do
      Norte/CE, num raio de aproximadamente 7 km do centro.
    </p>

    <EstadoDaTela
      :carregando="catalogo.carregandoMercados"
      :erro="catalogo.erro"
      :vazio="catalogo.mercados.length === 0"
      mensagem-carregando="Carregando mercados…"
      mensagem-vazio="Nenhum mercado cadastrado. Sem mercados não é possível gerar recomendação."
      @tentar-novamente="catalogo.carregarMercados(true)"
    >
      <ul class="colecao">
        <li v-for="mercado in catalogo.mercados" :key="mercado.id" class="cartao">
          <strong>{{ mercado.nome }}</strong>
          <p class="suave sem-margem">{{ mercado.endereco }}</p>
          <p class="suave coordenadas">
            {{ formatarCoordenada(mercado.latitude) }},
            {{ formatarCoordenada(mercado.longitude) }}
          </p>
        </li>
      </ul>
    </EstadoDaTela>
  </section>
</template>

<style scoped>
.colecao {
  list-style: none;
  padding: 0;
  margin: 0;
}

.sem-margem {
  margin: 0.15rem 0 0;
}

.coordenadas {
  margin: 0.25rem 0 0;
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
}
</style>
