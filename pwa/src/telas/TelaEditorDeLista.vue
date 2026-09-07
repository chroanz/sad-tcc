<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import EstadoDaTela from '@/componentes/EstadoDaTela.vue'
import { useCatalogoStore } from '@/stores/catalogo'
import { useListasStore } from '@/stores/listas'
import { formatarQuantidade } from '@/utilitarios/formato'
import type { Marca } from '@/api/tipos'

const props = defineProps<{ id: string }>()

const listas = useListasStore()
const catalogo = useCatalogoStore()

const listaId = computed<number>(() => Number(props.id))

const UNIDADES = ['un', 'kg', 'g', 'L', 'ml'] as const

const busca = ref('')
const produtoSelecionado = ref<number | null>(null)
const marcaSelecionada = ref<number | null>(null)
const quantidade = ref(1)
const unidade = ref<string>('un')
const marcasDoProduto = ref<Marca[]>([])

onMounted(() => {
  void listas.carregarLista(listaId.value)
  void catalogo.buscarProdutos()
})

// Buscar produtos a cada tecla geraria uma requisição por caractere; o atraso curto
// agrupa a digitação em uma consulta só.
let temporizadorBusca: ReturnType<typeof setTimeout> | undefined
watch(busca, (termo) => {
  clearTimeout(temporizadorBusca)
  temporizadorBusca = setTimeout(() => void catalogo.buscarProdutos(termo), 300)
})

watch(produtoSelecionado, async (produtoId) => {
  marcaSelecionada.value = null
  marcasDoProduto.value = produtoId ? await catalogo.carregarMarcas(produtoId) : []
})

const podeAdicionar = computed<boolean>(
  () => produtoSelecionado.value !== null && quantidade.value > 0
)

async function adicionar(): Promise<void> {
  if (!podeAdicionar.value || produtoSelecionado.value === null) return

  const adicionado = await listas.adicionarItem(listaId.value, {
    produto_id: produtoSelecionado.value,
    marca_id: marcaSelecionada.value,
    quantidade: quantidade.value,
    unidade: unidade.value
  })

  if (adicionado) {
    produtoSelecionado.value = null
    marcaSelecionada.value = null
    quantidade.value = 1
    unidade.value = 'un'
  }
}

async function remover(itemId: number): Promise<void> {
  await listas.removerItem(listaId.value, itemId)
}
</script>

<template>
  <section>
    <RouterLink :to="{ name: 'listas' }" class="voltar">← Minhas listas</RouterLink>
    <h1>{{ listas.listaAtual?.nome ?? 'Lista' }}</h1>

    <form class="cartao" @submit.prevent="adicionar">
      <h2>Adicionar item</h2>

      <label class="campo">
        <span>Buscar produto</span>
        <input v-model="busca" type="search" placeholder="Ex.: arroz" />
      </label>

      <label class="campo">
        <span>Produto</span>
        <select v-model="produtoSelecionado" required>
          <option :value="null" disabled>Selecione um produto</option>
          <option v-for="produto in catalogo.produtos" :key="produto.id" :value="produto.id">
            {{ produto.nome }} · {{ produto.categoria }}
          </option>
        </select>
      </label>

      <label class="campo">
        <span>Marca</span>
        <select v-model="marcaSelecionada" :disabled="produtoSelecionado === null">
          <option :value="null">Qualquer marca (costuma economizar mais)</option>
          <option v-for="marca in marcasDoProduto" :key="marca.id" :value="marca.id">
            {{ marca.nome }}
          </option>
        </select>
      </label>

      <div class="linha">
        <label class="campo crescer">
          <span>Quantidade</span>
          <input v-model.number="quantidade" type="number" min="0.001" step="0.001" required />
        </label>
        <label class="campo">
          <span>Unidade</span>
          <select v-model="unidade">
            <option v-for="opcao in UNIDADES" :key="opcao" :value="opcao">{{ opcao }}</option>
          </select>
        </label>
      </div>

      <button type="submit" class="largura-total" :disabled="!podeAdicionar || listas.salvando">
        {{ listas.salvando ? 'Salvando…' : 'Adicionar à lista' }}
      </button>
    </form>

    <h2>Itens da lista</h2>

    <EstadoDaTela
      :carregando="listas.carregando"
      :erro="listas.erro"
      :vazio="(listas.listaAtual?.itens.length ?? 0) === 0"
      mensagem-carregando="Carregando a lista…"
      mensagem-vazio="A lista está vazia. Adicione itens acima para poder gerar a recomendação."
      @tentar-novamente="listas.carregarLista(listaId)"
    >
      <ul class="colecao">
        <li v-for="item in listas.listaAtual?.itens ?? []" :key="item.id" class="cartao">
          <div class="linha-entre">
            <div>
              <strong>{{ item.produto_nome ?? `Produto ${item.produto_id}` }}</strong>
              <p class="suave sem-margem">
                {{ formatarQuantidade(item.quantidade, item.unidade) }} ·
                {{ item.marca_nome ?? 'qualquer marca' }}
              </p>
            </div>
            <button
              type="button"
              class="perigo"
              :aria-label="`Remover ${item.produto_nome ?? 'item'}`"
              @click="remover(item.id)"
            >
              Remover
            </button>
          </div>
        </li>
      </ul>

      <RouterLink
        :to="{ name: 'resultado', params: { id: listaId } }"
        class="botao-principal"
      >
        Gerar recomendação
      </RouterLink>
    </EstadoDaTela>
  </section>
</template>

<style scoped>
.voltar {
  display: inline-block;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
  text-decoration: none;
}

.colecao {
  list-style: none;
  padding: 0;
  margin: 0 0 1rem;
}

.sem-margem {
  margin: 0.15rem 0 0;
}

.crescer {
  flex: 1;
}

.linha {
  align-items: flex-end;
}

.botao-principal {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: var(--alvo-toque);
  background: var(--cor-primaria);
  color: #fff;
  font-weight: 600;
  border-radius: var(--raio);
  text-decoration: none;
}
</style>
