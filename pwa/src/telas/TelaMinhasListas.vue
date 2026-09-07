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
    <div class="cabecalho-tela">
      <h1>Minhas listas</h1>
      <p>Cada lista vira um roteiro de compra.</p>
    </div>

    <form class="cartao criar" @submit.prevent="criar">
      <label class="campo crescer">
        <span>Nova lista</span>
        <input
          v-model="nomeNovaLista"
          type="text"
          placeholder="Ex.: Compras do mês"
          maxlength="120"
        />
      </label>
      <button
        type="submit"
        class="botao botao--primario"
        :disabled="criando || nomeNovaLista.trim() === ''"
      >
        {{ criando ? 'Criando…' : 'Criar' }}
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
          <!-- O cartão inteiro abre a lista; as ações secundárias ficam abaixo. -->
          <RouterLink
            :to="{ name: 'editor-lista', params: { id: lista.id } }"
            class="lista-cabeca"
          >
            <span class="crescer">
              <strong class="lista-nome">{{ lista.nome }}</strong>
              <span class="mini bloco">
                <span class="selo selo--marca">{{ lista.quantidade_itens ?? 0 }} itens</span>
                <template v-if="lista.criado_em">
                  criada em {{ formatarDataHora(lista.criado_em) }}
                </template>
              </span>
            </span>
            <svg
              class="seta"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M9 6l6 6-6 6" />
            </svg>
          </RouterLink>

          <div class="lista-acoes">
            <RouterLink
              :to="{ name: 'resultado', params: { id: lista.id } }"
              class="botao botao--secundario botao--pequeno"
            >
              Ver recomendação
            </RouterLink>
            <RouterLink
              :to="{ name: 'historico', params: { id: lista.id } }"
              class="botao botao--fantasma botao--pequeno"
            >
              Histórico
            </RouterLink>
            <button
              type="button"
              class="botao botao--fantasma botao--pequeno excluir"
              :aria-label="`Excluir a lista ${lista.nome}`"
              @click="excluir(lista.id, lista.nome)"
            >
              Excluir
            </button>
          </div>
        </li>
      </ul>
    </EstadoDaTela>
  </section>
</template>

<style scoped>
.criar {
  display: flex;
  align-items: flex-end;
  gap: var(--esp-3);
}

.criar .campo {
  margin-bottom: 0;
}

.lista-cabeca {
  display: flex;
  align-items: center;
  gap: var(--esp-3);
  text-decoration: none;
  color: inherit;
  margin: calc(var(--esp-2) * -1);
  padding: var(--esp-2);
  border-radius: var(--raio-pequeno);
}

.lista-nome {
  display: block;
  font-size: var(--fonte-media);
  font-weight: var(--peso-forte);
  letter-spacing: -0.01em;
}

.bloco {
  display: flex;
  align-items: center;
  gap: var(--esp-2);
  margin-top: var(--esp-1);
}

.seta {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  color: var(--cor-texto-suave);
}

.lista-acoes {
  display: flex;
  flex-wrap: wrap;
  gap: var(--esp-2);
  margin-top: var(--esp-3);
  padding-top: var(--esp-3);
  border-top: 1px solid var(--cor-borda);
}

.excluir {
  margin-left: auto;
  /* O tom sólido reprova em AA sobre branco; o escuro entrega 7,6:1. */
  color: var(--cor-erro-texto);
}
</style>
