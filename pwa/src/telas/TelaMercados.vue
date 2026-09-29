<script setup lang="ts">
import { onMounted } from 'vue'
import EstadoDaTela from '@/componentes/EstadoDaTela.vue'
import { useCatalogoStore } from '@/stores/catalogo'
import { iniciaisDe, linkDoMapa } from '@/utilitarios/formato'

const catalogo = useCatalogoStore()

onMounted(() => {
  void catalogo.carregarMercados()
})
</script>

<template>
  <section>
    <div class="cabecalho-tela">
      <h1>Mercados</h1>
      <p>
        Supermercados considerados nas recomendações, todos em Juazeiro do Norte/CE. São
        fictícios: cada um pratica os preços da cesta básica do DIEESE da cidade que lhe dá
        nome.
      </p>
    </div>

    <EstadoDaTela
      :carregando="catalogo.carregandoMercados"
      :erro="catalogo.erro"
      :vazio="catalogo.mercados.length === 0"
      mensagem-carregando="Carregando mercados…"
      mensagem-vazio="Nenhum mercado cadastrado. Sem mercados não é possível gerar recomendação."
      @tentar-novamente="catalogo.carregarMercados(true)"
    >
      <ul class="colecao">
        <li v-for="mercado in catalogo.mercados" :key="mercado.id" class="cartao mercado">
          <span class="avatar" aria-hidden="true">{{ iniciaisDe(mercado.nome) }}</span>

          <div class="crescer">
            <strong>{{ mercado.nome }}</strong>
            <p class="mini endereco">{{ mercado.endereco }}</p>
            <!-- Coordenada crua é dado de depuração; o que serve ao usuário é chegar lá. -->
            <a
              class="botao botao--fantasma botao--pequeno mapa"
              :href="linkDoMapa(mercado.latitude, mercado.longitude, mercado.nome)"
              target="_blank"
              rel="noopener noreferrer"
            >
              Ver no mapa
            </a>
          </div>
        </li>
      </ul>
    </EstadoDaTela>
  </section>
</template>

<style scoped>
.mercado {
  display: flex;
  align-items: flex-start;
  gap: var(--esp-3);
}

.endereco {
  margin: 2px 0 var(--esp-2);
}

.mapa {
  margin-left: calc(var(--esp-4) * -1);
  color: var(--cor-marca-forte);
}
</style>
