import { computed, ref, type ComputedRef, type Ref } from 'vue'
import { defineStore } from 'pinia'
import {
  gerarRecomendacao as gerarRecomendacaoApi,
  listarHistorico as listarHistoricoApi,
  obterRecomendacao as obterRecomendacaoApi
} from '@/api/recomendacoes'
import { mensagemAmigavel } from '@/api/clienteHttp'
import { useOrigemStore } from '@/stores/origem'
import type { PerfilConveniencia, Recomendacao, RecomendacaoResumo } from '@/api/tipos'

/** Ordem de apresentação: do mais barato ao mais cômodo. */
export const PERFIS: readonly PerfilConveniencia[] = [
  'economico',
  'equilibrado',
  'conveniente'
] as const

export type ResultadosPorPerfil = Record<PerfilConveniencia, Recomendacao | null>

function semResultados(): ResultadosPorPerfil {
  return { economico: null, equilibrado: null, conveniente: null }
}

export interface RetornoRecomendacaoStore {
  resultadosPorPerfil: Ref<ResultadosPorPerfil>
  perfilSelecionado: Ref<PerfilConveniencia>
  selecionada: ComputedRef<Recomendacao | null>
  temResultados: ComputedRef<boolean>
  historico: Ref<RecomendacaoResumo[]>
  recomendacaoAberta: Ref<Recomendacao | null>
  gerando: Ref<boolean>
  carregando: Ref<boolean>
  erro: Ref<string | null>
  focarLista: (listaId: number) => void
  invalidarResultados: () => void
  gerarTodosOsPerfis: (listaId: number) => Promise<void>
  carregarHistorico: (listaId: number) => Promise<void>
  abrir: (recomendacaoId: number) => Promise<Recomendacao | null>
  limpar: () => void
  limparErro: () => void
}

export const useRecomendacaoStore = defineStore(
  'recomendacao',
  (): RetornoRecomendacaoStore => {
    const resultadosPorPerfil = ref<ResultadosPorPerfil>(semResultados())
    const perfilSelecionado = ref<PerfilConveniencia>('equilibrado')
    const historico = ref<RecomendacaoResumo[]>([])
    const recomendacaoAberta = ref<Recomendacao | null>(null)
    const gerando = ref(false)
    const carregando = ref(false)
    const erro = ref<string | null>(null)

    /**
     * Lista à qual os resultados em memória pertencem. Sem esse controle a store, que é
     * global, entregaria o resultado de uma lista na tela de outra.
     */
    const listaEmFoco = ref<number | null>(null)

    const selecionada = computed<Recomendacao | null>(
      () => resultadosPorPerfil.value[perfilSelecionado.value]
    )

    const temResultados = computed<boolean>(() =>
      PERFIS.some((perfil) => resultadosPorPerfil.value[perfil] !== null)
    )

    /**
     * Declara qual lista a tela está exibindo. Se for outra, tudo o que estava em memória
     * é descartado — é o que impede a tela de mostrar o roteiro da lista anterior.
     */
    function focarLista(listaId: number): void {
      if (listaEmFoco.value === listaId) return
      listaEmFoco.value = listaId
      resultadosPorPerfil.value = semResultados()
      recomendacaoAberta.value = null
      historico.value = []
      erro.value = null
    }

    /**
     * Descarta os perfis já calculados sem trocar a lista em foco. Chamado quando os itens
     * da lista mudam: o roteiro anterior deixou de corresponder ao que se quer comprar, e
     * exibi-lo seria pior do que não exibir nada.
     */
    function invalidarResultados(): void {
      resultadosPorPerfil.value = semResultados()
    }

    /**
     * Resolve os três perfis de uma vez. Cada execução leva dezenas de milissegundos, e
     * tê-los todos é o que permite mostrar o trade-off entre preço e deslocamento lado a
     * lado, em vez de obrigar o usuário a gerar um, memorizar e comparar de cabeça.
     *
     * Falhas são isoladas por perfil: se um não resolver, os demais continuam sendo
     * apresentados.
     */
    async function gerarTodosOsPerfis(listaId: number): Promise<void> {
      focarLista(listaId)
      gerando.value = true
      erro.value = null

      // Origem e raio andam juntos: filtrar por distância a partir de um ponto que não é
      // o do usuário transformaria "5 km de mim" em "5 km do centro".
      const origem = useOrigemStore()
      const execucoes = await Promise.allSettled(
        PERFIS.map((perfil) =>
          gerarRecomendacaoApi(listaId, {
            perfil,
            origem: origem.coordenadaParaEnvio,
            raio_km: origem.raioParaEnvio
          })
        )
      )

      const obtidos = semResultados()
      let ultimaFalha: unknown = null

      execucoes.forEach((execucao, indice) => {
        if (execucao.status === 'fulfilled') {
          obtidos[PERFIS[indice]] = execucao.value
        } else {
          ultimaFalha = execucao.reason
        }
      })

      resultadosPorPerfil.value = obtidos
      gerando.value = false

      if (!temResultados.value && ultimaFalha !== null) {
        erro.value = mensagemAmigavel(ultimaFalha)
      }
    }

    async function carregarHistorico(listaId: number): Promise<void> {
      focarLista(listaId)
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

    /**
     * Abrir do histórico apenas lê o resultado gravado: nunca recalcula. O resultado fica
     * em `recomendacaoAberta`, separado dos perfis gerados, para que consultar o histórico
     * não altere o que a tela de recomendação mostra.
     */
    async function abrir(recomendacaoId: number): Promise<Recomendacao | null> {
      carregando.value = true
      erro.value = null
      try {
        const recomendacao = await obterRecomendacaoApi(recomendacaoId)
        recomendacaoAberta.value = recomendacao
        return recomendacao
      } catch (falha) {
        erro.value = mensagemAmigavel(falha)
        return null
      } finally {
        carregando.value = false
      }
    }

    function limpar(): void {
      listaEmFoco.value = null
      resultadosPorPerfil.value = semResultados()
      recomendacaoAberta.value = null
      historico.value = []
      erro.value = null
    }

    function limparErro(): void {
      erro.value = null
    }

    return {
      resultadosPorPerfil,
      perfilSelecionado,
      selecionada,
      temResultados,
      historico,
      recomendacaoAberta,
      gerando,
      carregando,
      erro,
      focarLista,
      invalidarResultados,
      gerarTodosOsPerfis,
      carregarHistorico,
      abrir,
      limpar,
      limparErro
    }
  }
)
