import { ref, type Ref } from 'vue'
import { defineStore } from 'pinia'
import {
  adicionarItem as adicionarItemApi,
  atualizarItem as atualizarItemApi,
  criarLista as criarListaApi,
  excluirLista as excluirListaApi,
  listarListas,
  obterLista,
  removerItem as removerItemApi,
  renomearLista as renomearListaApi
} from '@/api/listas'
import { mensagemAmigavel } from '@/api/clienteHttp'
import { useRecomendacaoStore } from '@/stores/recomendacao'
import type { EntradaItemLista, ListaDetalhada, ListaResumo } from '@/api/tipos'

export interface RetornoListasStore {
  listas: Ref<ListaResumo[]>
  listaAtual: Ref<ListaDetalhada | null>
  carregando: Ref<boolean>
  salvando: Ref<boolean>
  erro: Ref<string | null>
  carregarListas: () => Promise<void>
  carregarLista: (listaId: number) => Promise<void>
  criarLista: (nome: string) => Promise<ListaResumo | null>
  renomearLista: (listaId: number, nome: string) => Promise<boolean>
  excluirLista: (listaId: number) => Promise<boolean>
  adicionarItem: (listaId: number, item: EntradaItemLista) => Promise<boolean>
  atualizarItem: (listaId: number, itemId: number, item: EntradaItemLista) => Promise<boolean>
  removerItem: (listaId: number, itemId: number) => Promise<boolean>
  limparErro: () => void
}

export const useListasStore = defineStore('listas', (): RetornoListasStore => {
  const listas = ref<ListaResumo[]>([])
  const listaAtual = ref<ListaDetalhada | null>(null)
  const carregando = ref(false)
  const salvando = ref(false)
  const erro = ref<string | null>(null)

  async function carregarListas(): Promise<void> {
    carregando.value = true
    erro.value = null
    try {
      listas.value = await listarListas()
    } catch (falha) {
      erro.value = mensagemAmigavel(falha)
    } finally {
      carregando.value = false
    }
  }

  async function carregarLista(listaId: number): Promise<void> {
    carregando.value = true
    erro.value = null
    try {
      listaAtual.value = await obterLista(listaId)
    } catch (falha) {
      erro.value = mensagemAmigavel(falha)
      listaAtual.value = null
    } finally {
      carregando.value = false
    }
  }

  /** Envolve uma escrita, cuidando de `salvando`/`erro` e devolvendo sucesso ou falha. */
  async function comSalvamento<T>(acao: () => Promise<T>): Promise<T | null> {
    salvando.value = true
    erro.value = null
    try {
      return await acao()
    } catch (falha) {
      erro.value = mensagemAmigavel(falha)
      return null
    } finally {
      salvando.value = false
    }
  }

  async function criarLista(nome: string): Promise<ListaResumo | null> {
    const criada = await comSalvamento(() => criarListaApi(nome))
    if (criada) await carregarListas()
    return criada
  }

  async function renomearLista(listaId: number, nome: string): Promise<boolean> {
    const atualizada = await comSalvamento(() => renomearListaApi(listaId, nome))
    if (!atualizada) return false
    listas.value = listas.value.map((lista) =>
      lista.id === listaId ? { ...lista, nome } : lista
    )
    if (listaAtual.value?.id === listaId) listaAtual.value = { ...listaAtual.value, nome }
    return true
  }

  async function excluirLista(listaId: number): Promise<boolean> {
    const resultado = await comSalvamento(async () => {
      await excluirListaApi(listaId)
      return true
    })
    if (!resultado) return false
    listas.value = listas.value.filter((lista) => lista.id !== listaId)
    if (listaAtual.value?.id === listaId) listaAtual.value = null
    return true
  }

  async function recarregarItens(listaId: number): Promise<void> {
    try {
      listaAtual.value = await obterLista(listaId)
    } catch (falha) {
      erro.value = mensagemAmigavel(falha)
    }
  }

  /**
   * Mexer nos itens invalida qualquer roteiro já calculado para a lista: ele foi resolvido
   * sobre outra cesta. Sem isso a tela de recomendação exibiria um resultado que não
   * corresponde mais ao que o usuário quer comprar.
   */
  function descartarRecomendacoes(): void {
    useRecomendacaoStore().invalidarResultados()
  }

  async function adicionarItem(listaId: number, item: EntradaItemLista): Promise<boolean> {
    const resultado = await comSalvamento(() => adicionarItemApi(listaId, item))
    if (!resultado) return false
    descartarRecomendacoes()
    await recarregarItens(listaId)
    return true
  }

  async function atualizarItem(
    listaId: number,
    itemId: number,
    item: EntradaItemLista
  ): Promise<boolean> {
    const resultado = await comSalvamento(() => atualizarItemApi(listaId, itemId, item))
    if (!resultado) return false
    descartarRecomendacoes()
    await recarregarItens(listaId)
    return true
  }

  async function removerItem(listaId: number, itemId: number): Promise<boolean> {
    const resultado = await comSalvamento(async () => {
      await removerItemApi(listaId, itemId)
      return true
    })
    if (!resultado) return false
    descartarRecomendacoes()
    if (listaAtual.value?.id === listaId) {
      listaAtual.value = {
        ...listaAtual.value,
        itens: listaAtual.value.itens.filter((item) => item.id !== itemId)
      }
    }
    return true
  }

  function limparErro(): void {
    erro.value = null
  }

  return {
    listas,
    listaAtual,
    carregando,
    salvando,
    erro,
    carregarListas,
    carregarLista,
    criarLista,
    renomearLista,
    excluirLista,
    adicionarItem,
    atualizarItem,
    removerItem,
    limparErro
  }
})
