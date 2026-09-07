import { ref, type Ref } from 'vue'
import { defineStore } from 'pinia'
import {
  gerarRecomendacao as gerarRecomendacaoApi,
  listarHistorico as listarHistoricoApi,
  obterRecomendacao as obterRecomendacaoApi
} from '@/api/recomendacoes'
import { mensagemAmigavel } from '@/api/clienteHttp'
import type { PedidoRecomendacao, Recomendacao, RecomendacaoResumo } from '@/api/tipos'

export interface RetornoRecomendacaoStore {
  atual: Ref<Recomendacao | null>
  historico: Ref<RecomendacaoResumo[]>
  gerando: Ref<boolean>
  carregando: Ref<boolean>
  erro: Ref<string | null>
  gerar: (listaId: number, pedido: PedidoRecomendacao) => Promise<Recomendacao | null>
  carregarHistorico: (listaId: number) => Promise<void>
  abrir: (recomendacaoId: number) => Promise<Recomendacao | null>
  limpar: () => void
  limparErro: () => void
}

export const useRecomendacaoStore = defineStore(
  'recomendacao',
  (): RetornoRecomendacaoStore => {
    const atual = ref<Recomendacao | null>(null)
    const historico = ref<RecomendacaoResumo[]>([])
    const gerando = ref(false)
    const carregando = ref(false)
    const erro = ref<string | null>(null)

    /**
     * Gerar é a operação mais lenta do sistema: percorre banco, montagem de payload e
     * solver CP-SAT. O estado `gerando` existe para a tela desabilitar o botão e mostrar
     * o carregamento, em vez de deixar o usuário achar que nada aconteceu.
     */
    async function gerar(
      listaId: number,
      pedido: PedidoRecomendacao
    ): Promise<Recomendacao | null> {
      gerando.value = true
      erro.value = null
      try {
        const recomendacao = await gerarRecomendacaoApi(listaId, pedido)
        atual.value = recomendacao
        return recomendacao
      } catch (falha) {
        erro.value = mensagemAmigavel(falha)
        return null
      } finally {
        gerando.value = false
      }
    }

    async function carregarHistorico(listaId: number): Promise<void> {
      carregando.value = true
      erro.value = null
      try {
        historico.value = await listarHistoricoApi(listaId)
      } catch (falha) {
        erro.value = mensagemAmigavel(falha)
      } finally {
        carregando.value = false
      }
    }

    /** Abrir do histórico apenas lê o resultado gravado: nunca recalcula. */
    async function abrir(recomendacaoId: number): Promise<Recomendacao | null> {
      carregando.value = true
      erro.value = null
      try {
        const recomendacao = await obterRecomendacaoApi(recomendacaoId)
        atual.value = recomendacao
        return recomendacao
      } catch (falha) {
        erro.value = mensagemAmigavel(falha)
        return null
      } finally {
        carregando.value = false
      }
    }

    function limpar(): void {
      atual.value = null
      historico.value = []
      erro.value = null
    }

    function limparErro(): void {
      erro.value = null
    }

    return {
      atual,
      historico,
      gerando,
      carregando,
      erro,
      gerar,
      carregarHistorico,
      abrir,
      limpar,
      limparErro
    }
  }
)
