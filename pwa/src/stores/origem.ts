import { computed, ref, type ComputedRef, type Ref } from 'vue'
import { defineStore } from 'pinia'
import { useCatalogoStore } from '@/stores/catalogo'
import {
  ErroDeLocalizacao,
  consultarPermissao,
  obterPosicao,
  suportaGeolocalizacao,
  type EstadoDaPermissao
} from '@/utilitarios/localizacao'
import { gravarJson, lerJson } from '@/utilitarios/armazenamento'
import type { Mercado, Origem } from '@/api/tipos'

/**
 * De onde o usuário parte e até onde aceita ir.
 *
 * As duas decisões vivem juntas porque são a mesma pergunta prática, e porque um raio sem
 * origem real seria um raio a partir do centro da cidade — o tipo de discrepância
 * silenciosa que a avaliação heurística classificou como o pior defeito possível.
 */

export type ModoDeOrigem = 'padrao' | 'dispositivo' | 'referencia'

/** Raios oferecidos; `null` significa "sem recorte". */
export const RAIOS_KM: readonly (number | null)[] = [2, 5, 7, 10, null] as const

/** Recorte declarado no plano de desenvolvimento para Juazeiro do Norte. */
export const RAIO_PADRAO_KM = 7

const CHAVE_PREFERENCIA = 'compra-certa:origem'

/**
 * Só a preferência é gravada — nunca a coordenada. Guardar a posição do usuário no
 * aparelho não traria ganho (obtê-la de novo é instantâneo quando a permissão já existe) e
 * criaria um dado pessoal persistido sem necessidade.
 */
interface PreferenciaGravada {
  modo: ModoDeOrigem
  mercadoReferenciaId: number | null
  raioKm: number | null
}

export interface RetornoOrigemStore {
  modo: Ref<ModoDeOrigem>
  coordenada: Ref<Origem | null>
  mercadoReferenciaId: Ref<number | null>
  raioKm: Ref<number | null>
  obtendo: Ref<boolean>
  erro: Ref<string | null>
  permissao: Ref<EstadoDaPermissao>
  disponivel: ComputedRef<boolean>
  coordenadaParaEnvio: ComputedRef<Origem | undefined>
  raioParaEnvio: ComputedRef<number | undefined>
  descricao: ComputedRef<string>
  restaurar: () => Promise<void>
  usarDispositivo: () => Promise<boolean>
  usarReferencia: (mercado: Mercado) => void
  usarPadrao: () => void
  definirRaio: (km: number | null) => void
  limparErro: () => void
}

export const useOrigemStore = defineStore('origem', (): RetornoOrigemStore => {
  const modo = ref<ModoDeOrigem>('padrao')
  const coordenada = ref<Origem | null>(null)
  const mercadoReferenciaId = ref<number | null>(null)
  const raioKm = ref<number | null>(RAIO_PADRAO_KM)
  const obtendo = ref(false)
  const erro = ref<string | null>(null)
  const permissao = ref<EstadoDaPermissao>('pendente')

  const disponivel = computed<boolean>(() => suportaGeolocalizacao())

  const coordenadaParaEnvio = computed<Origem | undefined>(() =>
    modo.value === 'padrao' || coordenada.value === null ? undefined : coordenada.value
  )

  /**
   * O raio só é enviado quando há origem real. Um recorte medido a partir da referência
   * padrão do servidor seria "5 km do centro" apresentado como "5 km de mim" — a mesma
   * discrepância silenciosa entre o que a tela diz e o que o sistema faz que a avaliação
   * heurística tratou como defeito mais grave.
   */
  const raioParaEnvio = computed<number | undefined>(() =>
    coordenadaParaEnvio.value === undefined ? undefined : (raioKm.value ?? undefined)
  )

  const descricao = computed<string>(() => {
    if (modo.value === 'dispositivo') return 'Sua localização atual'
    if (modo.value === 'referencia') {
      const catalogo = useCatalogoStore()
      const mercado = catalogo.mercados.find(
        (candidato) => candidato.id === mercadoReferenciaId.value
      )
      return mercado ? `Perto do ${mercado.nome}` : 'Ponto de referência escolhido'
    }
    return 'Centro de Juazeiro do Norte'
  })

  function gravarPreferencia(): void {
    gravarJson(CHAVE_PREFERENCIA, {
      modo: modo.value,
      mercadoReferenciaId: mercadoReferenciaId.value,
      raioKm: raioKm.value
    } satisfies PreferenciaGravada)
  }

  /**
   * A restauração é assíncrona e pode demorar — obter a posição do GPS leva segundos. Sem
   * memorizá-la, cada tela que precisasse da origem dispararia a sua, e quem gerasse uma
   * recomendação antes de ela terminar calcularia sem origem e sem raio, exibindo depois
   * uma tela que anuncia "sua localização · 7 km" sobre um resultado que não usou nenhum
   * dos dois.
   */
  let restauracao: Promise<void> | null = null

  function restaurar(): Promise<void> {
    restauracao ??= executarRestauracao()
    return restauracao
  }

  /**
   * Recompõe a escolha anterior. Quando o modo era o dispositivo e a permissão continua
   * concedida, a posição é buscada de novo em silêncio — nesse estado o navegador não
   * exibe aviso nenhum, então não há pedido sendo feito às escondidas.
   */
  async function executarRestauracao(): Promise<void> {
    permissao.value = await consultarPermissao()

    const gravada = lerJson<PreferenciaGravada>(CHAVE_PREFERENCIA)
    if (gravada === null) return

    raioKm.value = gravada.raioKm
    mercadoReferenciaId.value = gravada.mercadoReferenciaId

    if (gravada.modo === 'dispositivo' && permissao.value === 'concedida') {
      await usarDispositivo()
      return
    }

    if (gravada.modo === 'referencia' && gravada.mercadoReferenciaId !== null) {
      const catalogo = useCatalogoStore()
      await catalogo.carregarMercados()
      const mercado = catalogo.mercados.find(
        (candidato) => candidato.id === gravada.mercadoReferenciaId
      )
      if (mercado) {
        usarReferencia(mercado)
        return
      }
    }

    usarPadrao()
  }

  async function usarDispositivo(): Promise<boolean> {
    obtendo.value = true
    erro.value = null
    try {
      coordenada.value = await obterPosicao()
      modo.value = 'dispositivo'
      mercadoReferenciaId.value = null
      permissao.value = 'concedida'
      gravarPreferencia()
      return true
    } catch (falha) {
      if (falha instanceof ErroDeLocalizacao) {
        erro.value = falha.message
        if (falha.motivo === 'negada') permissao.value = 'negada'
        if (falha.motivo === 'sem-suporte') permissao.value = 'indisponivel'
      } else {
        erro.value = 'Não foi possível obter sua localização.'
      }
      return false
    } finally {
      obtendo.value = false
    }
  }

  /** Alternativa a quem negou a permissão: partir de um mercado conhecido. */
  function usarReferencia(mercado: Mercado): void {
    coordenada.value = { latitude: mercado.latitude, longitude: mercado.longitude }
    mercadoReferenciaId.value = mercado.id
    modo.value = 'referencia'
    erro.value = null
    gravarPreferencia()
  }

  function usarPadrao(): void {
    coordenada.value = null
    mercadoReferenciaId.value = null
    modo.value = 'padrao'
    erro.value = null
    gravarPreferencia()
  }

  function definirRaio(km: number | null): void {
    raioKm.value = km
    gravarPreferencia()
  }

  function limparErro(): void {
    erro.value = null
  }

  return {
    modo,
    coordenada,
    mercadoReferenciaId,
    raioKm,
    obtendo,
    erro,
    permissao,
    disponivel,
    coordenadaParaEnvio,
    raioParaEnvio,
    descricao,
    restaurar,
    usarDispositivo,
    usarReferencia,
    usarPadrao,
    definirRaio,
    limparErro
  }
})
