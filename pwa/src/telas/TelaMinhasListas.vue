<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import EstadoDaTela from '@/componentes/EstadoDaTela.vue'
import { useListasStore } from '@/stores/listas'
import { formatarDataHora } from '@/utilitarios/formato'

const listas = useListasStore()
const roteador = useRouter()

const nomeNovaLista = ref('')
const criando = ref(false)

onMounted(() => {
  void listas.carregarListas()
})

async function criar(): Promise<void> {
  const nome = nomeNovaLista.value.trim()
  if (nome === '') return

  criando.value = true
  const criada = await listas.criarLista(nome)
  criando.value = false

  if (criada) {
    nomeNovaLista.value = ''
    await roteador.push({ name: 'editor-lista', params: { id: criada.id } })
  }
}

async function excluir(listaId: number, nome: string): Promise<void> {
  if (!window.confirm(`Excluir a lista "${nome}"? Os itens serão removidos junto.`)) return
  await listas.excluirLista(listaId)
}
</script>

<template>
  <section>
    <h1>Minhas listas</h1>

    <form class="cartao" @submit.prevent="criar">
      <label class="campo">
        <span>Nova lista</span>
        <input
          v-model="nomeNovaLista"
          type="text"
          placeholder="Ex.: Compras do mês"
          maxlength="120"
        />
      </label>
      <button type="submit" :disabled="criando || nomeNovaLista.trim() === ''">
        {{ criando ? 'Criando…' : 'Criar lista' }}
      </button>
    </form>

    <EstadoDaTela
      :carregando="listas.carregando"
      :erro="listas.erro"
      :vazio="listas.listas.length === 0"
      mensagem-carregando="Carregando suas listas…"
      mensagem-vazio="Você ainda não tem listas. Crie a primeira acima e adicione os itens da sua cesta."
      @tentar-novamente="listas.carregarListas()"
    >
      <ul class="colecao">
        <li v-for="lista in listas.listas" :key="lista.id" class="cartao">
          <div class="linha-entre">
            <div>
              <RouterLink
                :to="{ name: 'editor-lista', params: { id: lista.id } }"
                class="titulo-lista"
              >
                {{ lista.nome }}
              </RouterLink>
              <p class="suave sem-margem">
                {{ lista.quantidade_itens ?? 0 }} item(ns)
                <template v-if="lista.criado_em">
                  · criada em {{ formatarDataHora(lista.criado_em) }}
                </template>
              </p>
            </div>
            <button
              type="button"
              class="perigo"
              :aria-label="`Excluir a lista ${lista.nome}`"
              @click="excluir(lista.id, lista.nome)"
            >
              Excluir
            </button>
          </div>

          <div class="linha acoes">
            <RouterLink :to="{ name: 'editor-lista', params: { id: lista.id } }">
              Editar itens
            </RouterLink>
            <RouterLink :to="{ name: 'resultado', params: { id: lista.id } }">
              Gerar recomendação
            </RouterLink>
            <RouterLink :to="{ name: 'historico', params: { id: lista.id } }">
              Histórico
            </RouterLink>
          </div>
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

.titulo-lista {
  font-weight: 700;
  font-size: 1.05rem;
  text-decoration: none;
}

.sem-margem {
  margin: 0.15rem 0 0;
}

.acoes {
  margin-top: 0.6rem;
  padding-top: 0.6rem;
  border-top: 1px solid var(--cor-borda);
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.9rem;
}
</style>
