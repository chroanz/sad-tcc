<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessaoStore } from '@/stores/sessao'
import { usarEstadoDeConexao } from '@/utilitarios/conexao'

const sessao = useSessaoStore()
const rota = useRoute()
const roteador = useRouter()
const { online } = usarEstadoDeConexao()

const mostrarBarra = computed<boolean>(() => sessao.autenticado && rota.name !== 'entrar')

function sair(): void {
  sessao.encerrar()
  void roteador.push({ name: 'entrar' })
}
</script>

<template>
  <header v-if="mostrarBarra" class="barra-topo">
    <div class="barra-conteudo">
      <RouterLink :to="{ name: 'listas' }" class="marca">Compra Certa</RouterLink>
      <nav class="navegacao">
        <RouterLink :to="{ name: 'listas' }">Listas</RouterLink>
        <RouterLink :to="{ name: 'mercados' }">Mercados</RouterLink>
        <button type="button" class="discreto" @click="sair">Sair</button>
      </nav>
    </div>
  </header>

  <!--
    O aviso de offline fica fora do <main> porque vale para qualquer tela: gerar
    recomendação exige rede, ainda que as telas já visitadas abram do cache.
  -->
  <p v-if="!online" class="aviso atencao sem-conexao" role="status">
    Você está offline. As telas já visitadas continuam abrindo, mas gerar recomendação
    precisa de conexão.
  </p>

  <main class="conteudo">
    <RouterView />
  </main>
</template>

<style scoped>
.barra-topo {
  background: var(--cor-superficie);
  border-bottom: 1px solid var(--cor-borda);
  position: sticky;
  top: 0;
  z-index: 10;
}

.barra-conteudo {
  max-width: 720px;
  margin: 0 auto;
  padding: 0.5rem 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.marca {
  font-weight: 700;
  color: var(--cor-texto);
  text-decoration: none;
  font-size: 1rem;
}

.navegacao {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.navegacao a {
  min-height: var(--alvo-toque);
  display: inline-flex;
  align-items: center;
  padding: 0 0.6rem;
  border-radius: var(--raio);
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--cor-texto-suave);
}

.navegacao a.router-link-exact-active {
  color: var(--cor-primaria);
  background: var(--cor-fundo);
}

.sem-conexao {
  max-width: 720px;
  margin: 0.75rem auto 0;
}
</style>
