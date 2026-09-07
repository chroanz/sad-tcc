import { extrairLista, requisitar } from './clienteHttp'
import type { EntradaItemLista, ItemLista, ListaDetalhada, ListaResumo } from './tipos'

/**
 * O contrato descreve `GET /listas` como "listas do usuário, com contagem de itens" sem
 * fixar o nome do campo de contagem. Aceitamos os apelidos mais prováveis.
 */
function normalizarResumo(bruto: Record<string, unknown>): ListaResumo {
  const contagem =
    bruto.quantidade_itens ?? bruto.total_itens ?? bruto.qtd_itens ?? bruto.itens_count
  return {
    id: Number(bruto.id),
    nome: String(bruto.nome ?? ''),
    criado_em: typeof bruto.criado_em === 'string' ? bruto.criado_em : undefined,
    quantidade_itens: typeof contagem === 'number' ? contagem : undefined
  }
}

export async function listarListas(): Promise<ListaResumo[]> {
  const corpo = await requisitar<unknown>('/listas')
  return extrairLista<Record<string, unknown>>(corpo).map(normalizarResumo)
}

export async function obterLista(listaId: number): Promise<ListaDetalhada> {
  const corpo = await requisitar<Record<string, unknown>>(`/listas/${listaId}`)
  const itens = extrairLista<ItemLista>(corpo?.itens ?? [])
  return { ...normalizarResumo(corpo ?? {}), itens }
}

export function criarLista(nome: string): Promise<ListaResumo> {
  return requisitar<ListaResumo>('/listas', { metodo: 'POST', corpo: { nome } })
}

export function renomearLista(listaId: number, nome: string): Promise<ListaResumo> {
  return requisitar<ListaResumo>(`/listas/${listaId}`, { metodo: 'PUT', corpo: { nome } })
}

export function excluirLista(listaId: number): Promise<void> {
  return requisitar<void>(`/listas/${listaId}`, { metodo: 'DELETE' })
}

export function adicionarItem(listaId: number, item: EntradaItemLista): Promise<ItemLista> {
  return requisitar<ItemLista>(`/listas/${listaId}/itens`, { metodo: 'POST', corpo: item })
}

export function atualizarItem(
  listaId: number,
  itemId: number,
  item: EntradaItemLista
): Promise<ItemLista> {
  return requisitar<ItemLista>(`/listas/${listaId}/itens/${itemId}`, {
    metodo: 'PUT',
    corpo: item
  })
}

export function removerItem(listaId: number, itemId: number): Promise<void> {
  return requisitar<void>(`/listas/${listaId}/itens/${itemId}`, { metodo: 'DELETE' })
}
