import type { Origem } from '@/api/tipos'

/**
 * Acesso à geolocalização do navegador.
 *
 * A negação é definitiva: uma vez que o usuário recusa, a aplicação não consegue perguntar
 * de novo — só as configurações do navegador revertem. Por isso `obterPosicao` nunca deve
 * ser chamada no carregamento da tela, e sim depois de um toque explícito em que o usuário
 * já leu para que serve. Quem orquestra isso é a store `origem`.
 */

export type EstadoDaPermissao = 'concedida' | 'pendente' | 'negada' | 'indisponivel'

/** Raio médio da Terra em km, o mesmo valor usado pelo otimizador. */
const RAIO_DA_TERRA_KM = 6371.0088

/**
 * Distância em linha reta entre dois pontos, pela fórmula de haversine.
 *
 * Replica o cálculo do otimizador para que o cliente possa antecipar quantos mercados
 * caem no raio escolhido, sem ida ao servidor. É estimativa de apoio à escolha, nunca
 * insumo de decisão: a alocação continua vindo inteira do modelo.
 */
export function distanciaKm(de: Origem, para: Origem): number {
  const emRadianos = (graus: number): number => (graus * Math.PI) / 180

  const deltaLatitude = emRadianos(para.latitude - de.latitude)
  const deltaLongitude = emRadianos(para.longitude - de.longitude)

  const termo =
    Math.sin(deltaLatitude / 2) ** 2 +
    Math.cos(emRadianos(de.latitude)) *
      Math.cos(emRadianos(para.latitude)) *
      Math.sin(deltaLongitude / 2) ** 2

  return 2 * RAIO_DA_TERRA_KM * Math.asin(Math.sqrt(termo))
}

export type MotivoDaFalha = 'negada' | 'indisponivel' | 'tempo' | 'sem-suporte'

export class ErroDeLocalizacao extends Error {
  readonly motivo: MotivoDaFalha

  constructor(motivo: MotivoDaFalha, mensagem: string) {
    super(mensagem)
    this.name = 'ErroDeLocalizacao'
    this.motivo = motivo
  }
}

const MENSAGENS: Record<MotivoDaFalha, string> = {
  negada:
    'Você não permitiu o acesso à localização. Para liberar, ajuste as permissões do site ' +
    'no navegador — ou escolha um ponto de partida abaixo.',
  indisponivel:
    'O aparelho não conseguiu determinar sua localização agora. Escolha um ponto de partida ' +
    'abaixo.',
  tempo: 'A localização demorou demais para responder. Tente de novo ou escolha um ponto.',
  'sem-suporte':
    'Este navegador não oferece localização nesta página. Ela exige uma conexão segura ' +
    '(HTTPS): abrindo o app pelo endereço de rede, sem HTTPS, o recurso fica indisponível.'
}

/**
 * A API só existe em contexto seguro. Abrir o PWA pelo IP da máquina em HTTP — o que
 * acontece ao testar no celular com `vite --host` — deixa `navigator.geolocation`
 * inutilizável, e é preciso dizer isso ao usuário em vez de falhar em silêncio.
 */
export function suportaGeolocalizacao(): boolean {
  return typeof navigator !== 'undefined' && 'geolocation' in navigator && window.isSecureContext
}

/** Lê o estado da permissão sem disparar o aviso do navegador. */
export async function consultarPermissao(): Promise<EstadoDaPermissao> {
  if (!suportaGeolocalizacao()) return 'indisponivel'
  if (!('permissions' in navigator)) return 'pendente'

  try {
    const estado = await navigator.permissions.query({ name: 'geolocation' })
    if (estado.state === 'granted') return 'concedida'
    if (estado.state === 'denied') return 'negada'
    return 'pendente'
  } catch {
    // Navegadores sem suporte a `permissions` para geolocalização caem aqui; tratamos
    // como "ainda não sabemos", que é o estado que leva ao pedido explícito.
    return 'pendente'
  }
}

/**
 * Opções deliberadamente frugais: os mercados estão a quilômetros de distância, então a
 * precisão fina do GPS só gastaria bateria, e uma posição de poucos minutos atrás serve
 * perfeitamente para calcular distância até um supermercado.
 */
const OPCOES: PositionOptions = {
  enableHighAccuracy: false,
  timeout: 10_000,
  maximumAge: 300_000
}

function traduzirFalha(erro: GeolocationPositionError): ErroDeLocalizacao {
  if (erro.code === erro.PERMISSION_DENIED) {
    return new ErroDeLocalizacao('negada', MENSAGENS.negada)
  }
  if (erro.code === erro.TIMEOUT) {
    return new ErroDeLocalizacao('tempo', MENSAGENS.tempo)
  }
  return new ErroDeLocalizacao('indisponivel', MENSAGENS.indisponivel)
}

/**
 * Pede a posição atual. Dispara o aviso do navegador quando a permissão ainda não foi
 * decidida, então só deve ser chamada a partir de uma ação do usuário.
 */
export function obterPosicao(): Promise<Origem> {
  if (!suportaGeolocalizacao()) {
    return Promise.reject(new ErroDeLocalizacao('sem-suporte', MENSAGENS['sem-suporte']))
  }

  return new Promise<Origem>((resolver, rejeitar) => {
    navigator.geolocation.getCurrentPosition(
      (posicao) =>
        resolver({
          latitude: posicao.coords.latitude,
          longitude: posicao.coords.longitude
        }),
      (erro) => rejeitar(traduzirFalha(erro)),
      OPCOES
    )
  })
}
