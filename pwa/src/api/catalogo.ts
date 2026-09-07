import { extrairLista, requisitar } from './clienteHttp'
import type { Marca, Mercado, Produto } from './tipos'

export async function listarProdutos(busca?: string): Promise<Produto[]> {
  const corpo = await requisitar<unknown>('/produtos', { parametros: { busca } })
  return extrairLista<Produto>(corpo)
}

export async function listarMarcasDoProduto(produtoId: number): Promise<Marca[]> {
  const corpo = await requisitar<unknown>(`/produtos/${produtoId}/marcas`)
  return extrairLista<Marca>(corpo)
}

export async function listarMercados(): Promise<Mercado[]> {
  const corpo = await requisitar<unknown>('/mercados')
  return extrairLista<Mercado>(corpo)
}
