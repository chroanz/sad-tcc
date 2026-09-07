<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessaoStore } from '@/stores/sessao'
import { usarEstadoDeConexao } from '@/utilitarios/conexao'

const sessao = useSessaoStore()
const rota = useRoute()
const roteador = useRouter()
const { online } = usarEstadoDeConexao()

const mostrarCasca = computed<boolean>(() => sessao.autenticado && rota.name !== 'entrar')

function sair(): void {
  sessao.encerrar()
  void roteador.push({ name: 'entrar' })
}
</script>

<template>
  <header v-if="mostrarCasca" class="barra-topo">
    <div class="barra-topo__interno">
      <RouterLink :to="{ name: 'listas' }" class="marca">
        <span class="marca__sinal" aria-hidden="true">CC</span>
        Compra Certa
      </RouterLink>
      <button type="button" class="botao botao--fantasma botao--pequeno" @click="sair">
        Sair
      </button>
    </div>
  </header>

  <!--
    O aviso de offline fica fora do <main> porque vale para qualquer tela: gerar
    recomendação exige rede, ainda que as telas já visitadas abram do cache.
  -->
  <p v-if="!online" class="faixa-offline" role="status">
    Sem conexão. As telas já visitadas continuam abrindo, mas gerar recomendação precisa de
    internet.
  </p>

  <main class="conteudo">
    <RouterView />
  </main>

  <!--
    Menu inferior: com os destinos permanentemente visíveis e ao alcance do polegar, o
    usuário reconhece para onde pode ir em vez de precisar lembrar.
  -->
  <nav v-if="mostrarCasca" class="barra-navegacao" aria-label="Navegação principal">
    <RouterLink :to="{ name: 'listas' }" class="barra-navegacao__item">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M9 4h6a1 1 0 0 1 1 1v1H8V5a1 1 0 0 1 1-1z" />
        <path d="M8 6H6a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V7a1 1 0 0 0-1-1h-2" />
        <path d="M9 12l1.5 1.5L13.5 10" />
        <path d="M9 17h6" />
      </svg>
      Listas
    </RouterLink>

    <RouterLink :to="{ name: 'mercados' }" class="barra-navegacao__item">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M4 9h16l-1.2-4H5.2L4 9z" />
        <path d="M5.5 9v10a1 1 0 0 0 1 1h11a1 1 0 0 0 1-1V9" />
        <path d="M9.5 20v-5h5v5" />
      </svg>
      Mercados
    </RouterLink>
  </nav>
</template>

<style scoped>
.faixa-offline {
  position: sticky;
  top: var(--alvo-confortavel);
  z-index: 15;
  margin: 0;
  padding: var(--esp-2) var(--esp-4);
  background: var(--cor-destaque-tenue);
  border-bottom: 1px solid var(--cor-destaque-borda);
  color: var(--cor-destaque-texto);
  font-size: var(--fonte-mini);
  font-weight: var(--peso-medio);
  text-align: center;
}
</style>
