import { ref, type Ref } from 'vue'
import { defineStore } from 'pinia'
import { listarMarcasDoProduto, listarMercados, listarProdutos } from '@/api/catalogo'
import { mensagemAmigavel } from '@/api/clienteHttp'
import type { Marca, Mercado, Produto } from '@/api/tipos'

export interface RetornoCatalogoStore {
  produtos: Ref<Produto[]>
  mercados: Ref<Mercado[]>
  marcasPorProduto: Ref<Record<number, Marca[]>>
  carregandoProdutos: Ref<boolean>
  carregandoMercados: Ref<boolean>
  erro: Ref<string | null>
  buscarProdutos: (busca?: string) => Promise<void>
  carregarMercados: (forcar?: boolean) => Promise<void>
  carregarMarcas: (produtoId: number) => Promise<Marca[]>
  limparErro: () => void
}

export const useCatalogoStore = defineStore('catalogo', (): RetornoCatalogoStore => {
  const produtos = ref<Produto[]>([])
  const mercados = ref<Mercado[]>([])
  const marcasPorProduto = ref<Record<number, Marca[]>>({})
  const carregandoProdutos = ref(false)
  const carregandoMercados = ref(false)
  const erro = ref<string | null>(null)

  let contadorBusca = 0

  async function buscarProdutos(busca?: string): Promise<void> {
    const requisicao = ++contadorBusca
    carregandoProdutos.value = true
    erro.value = null
    try {
      const resultado = await listarProdutos(busca)
      // Ignora respostas de buscas antigas que chegaram fora de ordem.
      if (requisicao === contadorBusca) produtos.value = resultado
    } catch (falha) {
      if (requisicao === contadorBusca) {
        erro.value = mensagemAmigavel(falha)
        produtos.value = []
      }
    } finally {
      if (requisicao === contadorBusca) carregandoProdutos.value = false
    }
  }

  async function carregarMercados(forcar = false): Promise<void> {
    if (!forcar && mercados.value.length > 0) return
    carregandoMercados.value = true
    erro.value = null
    try {
      mercados.value = await listarMercados()
    } catch (falha) {
      erro.value = mensagemAmigavel(falha)
    } finally {
      carregandoMercados.value = false
    }
  }

  async function carregarMarcas(produtoId: number): Promise<Marca[]> {
    const jaCarregadas = marcasPorProduto.value[produtoId]
    if (jaCarregadas) return jaCarregadas
    try {
      const marcas = await listarMarcasDoProduto(produtoId)
      marcasPorProduto.value = { ...marcasPorProduto.value, [produtoId]: marcas }
      return marcas
    } catch (falha) {
      erro.value = mensagemAmigavel(falha)
      return []
    }
  }

  function limparErro(): void {
    erro.value = null
  }

  return {
    produtos,
    mercados,
    marcasPorProduto,
    carregandoProdutos,
    carregandoMercados,
    erro,
    buscarProdutos,
    carregarMercados,
    carregarMarcas,
    limparErro
  }
})
