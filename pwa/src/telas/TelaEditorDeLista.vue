<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import EstadoDaTela from '@/componentes/EstadoDaTela.vue'
import { useCatalogoStore } from '@/stores/catalogo'
import { useListasStore } from '@/stores/listas'
import { formatarQuantidade } from '@/utilitarios/formato'
import type { ItemLista, Marca, Produto } from '@/api/tipos'

const props = defineProps<{ id: string }>()

const listas = useListasStore()
const catalogo = useCatalogoStore()

const listaId = computed<number>(() => Number(props.id))

/** Teto imposto pela API; ver "limites" em docs/contrato-api-rest.md. */
const MAXIMO_ITENS = 20

const UNIDADES = ['un', 'kg', 'g', 'L', 'ml'] as const

const busca = ref('')
const produtoEscolhido = ref<Produto | null>(null)
const marcaSelecionada = ref<number | null>(null)
const quantidade = ref(1)
const unidade = ref<string>('un')
const marcasDoProduto = ref<Marca[]>([])
const avisoDeInclusao = ref('')

/** Quando preenchido, o formulário edita este item em vez de incluir um novo. */
const itemEmEdicao = ref<ItemLista | null>(null)

const renomeando = ref(false)
const nomeEditado = ref('')

const quantidadeDeItens = computed<number>(() => listas.listaAtual?.itens.length ?? 0)
const listaCheia = computed<boolean>(() => quantidadeDeItens.value >= MAXIMO_ITENS)
const quaseCheia = computed<boolean>(() => quantidadeDeItens.value >= MAXIMO_ITENS - 2)

const sugestoes = computed<Produto[]>(() =>
  produtoEscolhido.value === null ? catalogo.produtos.slice(0, 8) : []
)

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

async function escolherProduto(produto: Produto): Promise<void> {
  produtoEscolhido.value = produto
  marcaSelecionada.value = null
  avisoDeInclusao.value = ''
  marcasDoProduto.value = await catalogo.carregarMarcas(produto.id)
}

function cancelarEscolha(): void {
  produtoEscolhido.value = null
  itemEmEdicao.value = null
  marcaSelecionada.value = null
  quantidade.value = 1
  unidade.value = 'un'
}

/**
 * Traz um item já incluído de volta ao formulário. Sem isso, corrigir a quantidade exigia
 * remover e recriar o item do zero, embora a API de atualização sempre tenha existido.
 */
async function editarItem(item: ItemLista): Promise<void> {
  itemEmEdicao.value = item
  produtoEscolhido.value = {
    id: item.produto_id,
    nome: item.produto_nome ?? `Produto ${item.produto_id}`,
    categoria: ''
  }
  marcaSelecionada.value = item.marca_id
  quantidade.value = item.quantidade
  unidade.value = item.unidade
  avisoDeInclusao.value = ''
  marcasDoProduto.value = await catalogo.carregarMarcas(item.produto_id)
}

function iniciarRenomear(): void {
  nomeEditado.value = listas.listaAtual?.nome ?? ''
  renomeando.value = true
}

async function salvarNome(): Promise<void> {
  const nome = nomeEditado.value.trim()
  if (nome === '' || nome === listas.listaAtual?.nome) {
    renomeando.value = false
    return
  }
  if (await listas.renomearLista(listaId.value, nome)) renomeando.value = false
}

function ajustarQuantidade(passo: number): void {
  const proxima = Number((quantidade.value + passo).toFixed(3))
  quantidade.value = proxima < 0.001 ? 0.001 : proxima
}

const podeSalvar = computed<boolean>(
  () =>
    produtoEscolhido.value !== null &&
    quantidade.value > 0 &&
    (itemEmEdicao.value !== null || !listaCheia.value)
)

async function salvar(): Promise<void> {
  const produto = produtoEscolhido.value
  if (!podeSalvar.value || produto === null) return

  const entrada = {
    produto_id: produto.id,
    marca_id: marcaSelecionada.value,
    quantidade: quantidade.value,
    unidade: unidade.value
  }

  const emEdicao = itemEmEdicao.value
  const gravado = emEdicao
    ? await listas.atualizarItem(listaId.value, emEdicao.id, entrada)
    : await listas.adicionarItem(listaId.value, entrada)

  if (gravado) {
    // Em tela de celular a lista costuma estar fora do campo de visão; o anúncio confirma
    // a operação sem depender de o usuário rolar até lá.
    avisoDeInclusao.value = emEdicao
      ? `${produto.nome} atualizado.`
      : `${produto.nome} adicionado à lista.`
    busca.value = ''
    cancelarEscolha()
  }
}

async function remover(itemId: number): Promise<void> {
  await listas.removerItem(listaId.value, itemId)
}
</script>

<template>
  <section>
    <RouterLink :to="{ name: 'listas' }" class="voltar">
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
      Minhas listas
    </RouterLink>

    <div class="cabecalho-tela">
      <form v-if="renomeando" class="renomear" @submit.prevent="salvarNome">
        <label class="campo crescer">
          <span class="oculto-visual">Nome da lista</span>
          <input v-model="nomeEditado" type="text" maxlength="120" autofocus />
        </label>
        <button type="submit" class="botao botao--primario botao--pequeno">Salvar</button>
        <button
          type="button"
          class="botao botao--fantasma botao--pequeno"
          @click="renomeando = false"
        >
          Cancelar
        </button>
      </form>

      <div v-else class="linha-entre">
        <h1 class="crescer">{{ listas.listaAtual?.nome ?? 'Lista' }}</h1>
        <button
          type="button"
          class="botao botao--fantasma botao--pequeno"
          @click="iniciarRenomear"
        >
          Renomear
        </button>
      </div>
      <!-- O teto aparece antes de ser violado, em vez de virar um erro 400 no 21º item. -->
      <p>
        <span :class="quaseCheia ? 'selo selo--destaque' : 'selo selo--marca'">
          {{ quantidadeDeItens }} de {{ MAXIMO_ITENS }} itens
        </span>
      </p>
    </div>

    <p v-if="listaCheia" class="aviso aviso--atencao">
      A lista chegou ao limite de {{ MAXIMO_ITENS }} itens. Remova algum para incluir outro.
    </p>

    <div class="cartao">
      <!-- Um controle só para escolher o produto: digita, vê e toca. -->
      <template v-if="produtoEscolhido === null">
        <label class="busca">
          <span class="oculto-visual">Buscar produto</span>
          <svg
            class="busca__icone"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="M20 20l-3.5-3.5" />
          </svg>
          <input
            v-model="busca"
            type="search"
            placeholder="Buscar produto. Ex.: arroz"
            :disabled="listaCheia"
          />
        </label>

        <p v-if="catalogo.carregandoProdutos" class="mini">Buscando…</p>
        <p v-else-if="sugestoes.length === 0" class="mini">
          Nenhum produto encontrado para "{{ busca }}".
        </p>

        <ul v-else class="sugestoes">
          <li v-for="produto in sugestoes" :key="produto.id">
            <button
              type="button"
              class="sugestao"
              :disabled="listaCheia"
              @click="escolherProduto(produto)"
            >
              <span class="crescer">
                <strong>{{ produto.nome }}</strong>
                <span class="mini bloco">{{ produto.categoria }}</span>
              </span>
              <span class="mais" aria-hidden="true">+</span>
            </button>
          </li>
        </ul>
      </template>

      <!-- Produto escolhido: só o que falta decidir fica na tela. -->
      <form v-else class="escolhido" @submit.prevent="salvar">
        <div class="linha-entre">
          <div>
            <strong>{{ produtoEscolhido.nome }}</strong>
            <p class="mini sem-margem">
              {{ itemEmEdicao ? 'Editando um item da lista' : produtoEscolhido.categoria }}
            </p>
          </div>
          <button type="button" class="botao botao--fantasma botao--pequeno" @click="cancelarEscolha">
            {{ itemEmEdicao ? 'Cancelar' : 'Trocar' }}
          </button>
        </div>

        <label class="campo">
          <span>Marca</span>
          <select v-model="marcaSelecionada">
            <option :value="null">Qualquer marca (costuma economizar mais)</option>
            <option v-for="marca in marcasDoProduto" :key="marca.id" :value="marca.id">
              {{ marca.nome }}
            </option>
          </select>
        </label>

        <div class="linha quantidade">
          <div class="campo">
            <span>Quantidade</span>
            <div class="passo">
              <button
                type="button"
                :disabled="quantidade <= 0.001"
                aria-label="Diminuir quantidade"
                @click="ajustarQuantidade(-1)"
              >
                −
              </button>
              <input
                v-model.number="quantidade"
                type="number"
                min="0.001"
                step="0.001"
                aria-label="Quantidade"
                required
              />
              <button type="button" aria-label="Aumentar quantidade" @click="ajustarQuantidade(1)">
                +
              </button>
            </div>
          </div>

          <label class="campo crescer">
            <span>Unidade</span>
            <select v-model="unidade">
              <option v-for="opcao in UNIDADES" :key="opcao" :value="opcao">{{ opcao }}</option>
            </select>
          </label>
        </div>

        <button
          type="submit"
          class="botao botao--primario botao--bloco"
          :disabled="!podeSalvar || listas.salvando"
        >
          {{
            listas.salvando
              ? 'Salvando…'
              : itemEmEdicao
                ? 'Salvar alterações'
                : 'Adicionar à lista'
          }}
        </button>
      </form>
    </div>

    <p v-if="avisoDeInclusao" class="aviso aviso--sucesso" role="status">
      {{ avisoDeInclusao }}
    </p>

    <h2>Itens da lista</h2>

    <EstadoDaTela
      :carregando="listas.carregando"
      :erro="listas.erro"
      :vazio="quantidadeDeItens === 0"
      :esqueletos="2"
      mensagem-carregando="Carregando a lista…"
      mensagem-vazio="A lista está vazia. Busque um produto acima para começar."
      @tentar-novamente="listas.carregarLista(listaId)"
    >
      <ul class="colecao">
        <li v-for="item in listas.listaAtual?.itens ?? []" :key="item.id" class="cartao item">
          <div class="linha-entre">
            <div class="crescer">
              <strong>{{ item.produto_nome ?? `Produto ${item.produto_id}` }}</strong>
              <p class="mini sem-margem">
                {{ formatarQuantidade(item.quantidade, item.unidade) }} ·
                {{ item.marca_nome ?? 'qualquer marca' }}
              </p>
            </div>
            <button
              type="button"
              class="botao botao--fantasma botao--pequeno"
              :aria-label="`Editar ${item.produto_nome ?? 'item'}`"
              @click="editarItem(item)"
            >
              Editar
            </button>
            <button
              type="button"
              class="botao botao--fantasma botao--pequeno remover"
              :aria-label="`Remover ${item.produto_nome ?? 'item'}`"
              @click="remover(item.id)"
            >
              Remover
            </button>
          </div>
        </li>
      </ul>
    </EstadoDaTela>

    <!-- A ação principal acompanha a rolagem, com o estado da lista sempre à vista. -->
    <div v-if="quantidadeDeItens > 0" class="barra-acao">
      <div class="barra-acao__interno">
        <span class="barra-acao__resumo">
          <span class="barra-acao__rotulo">Sua lista</span>
          <span class="barra-acao__valor">{{ quantidadeDeItens }} itens</span>
        </span>
        <RouterLink
          :to="{ name: 'resultado', params: { id: listaId } }"
          class="botao botao--primario"
        >
          Gerar recomendação
        </RouterLink>
      </div>
    </div>
  </section>
</template>

<style scoped>
.voltar svg {
  width: 16px;
  height: 16px;
}

.cabecalho-tela p {
  margin-top: var(--esp-2);
}

.sugestoes {
  list-style: none;
  padding: 0;
  margin: 0;
}

.sugestao {
  display: flex;
  align-items: center;
  gap: var(--esp-3);
  width: 100%;
  min-height: var(--alvo-confortavel);
  padding: var(--esp-2);
  text-align: left;
  background: none;
  border: none;
  border-bottom: 1px solid var(--cor-borda);
  border-radius: var(--raio-pequeno);
  color: inherit;
  font: inherit;
  cursor: pointer;
}

.sugestao:hover:not(:disabled) {
  background: var(--cor-superficie-alt);
}

.sugestao:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mais {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--cor-marca-tenue);
  color: var(--cor-marca-forte);
  font-weight: var(--peso-forte);
}

.bloco {
  display: block;
  margin-top: 2px;
}

.sem-margem {
  margin: 2px 0 0;
}

.escolhido .linha-entre {
  margin-bottom: var(--esp-4);
}

.quantidade {
  align-items: flex-end;
  gap: var(--esp-3);
}

.quantidade .campo {
  margin-bottom: var(--esp-4);
}

.item {
  padding: var(--esp-3) var(--esp-4);
}

.renomear {
  display: flex;
  align-items: flex-end;
  gap: var(--esp-2);
  flex-wrap: wrap;
}

.renomear .campo {
  margin-bottom: 0;
  min-width: 12rem;
}

.remover {
  color: var(--cor-erro-texto);
}
</style>
