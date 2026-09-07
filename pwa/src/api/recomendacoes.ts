import { extrairLista, requisitar } from './clienteHttp'
import type { PedidoRecomendacao, Recomendacao, RecomendacaoResumo } from './tipos'

/** Operação lenta: chama o solver CP-SAT através da API Go. */
export function gerarRecomendacao(
  listaId: number,
  pedido: PedidoRecomendacao
): Promise<Recomendacao> {
  return requisitar<Recomendacao>(`/listas/${listaId}/recomendacoes`, {
    metodo: 'POST',
    corpo: pedido
  })
}

export async function listarHistorico(listaId: number): Promise<RecomendacaoResumo[]> {
  const corpo = await requisitar<unknown>(`/listas/${listaId}/recomendacoes`)
  return extrairLista<RecomendacaoResumo>(corpo)
}

/** Recomendações são imutáveis: abrir do histórico apenas lê, nunca recalcula. */
export function obterRecomendacao(recomendacaoId: number): Promise<Recomendacao> {
  return requisitar<Recomendacao>(`/recomendacoes/${recomendacaoId}`)
}
