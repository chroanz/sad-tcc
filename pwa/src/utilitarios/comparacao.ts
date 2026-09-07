import { formatarDistancia, formatarReais } from '@/utilitarios/formato'
import type { Recomendacao } from '@/api/tipos'

/**
 * Comparação entre dois perfis de compra, em linguagem de decisão.
 *
 * O sistema não sabe quanto vale um quilômetro para quem vai comprar: o
 * `custo_por_km_centavos` é um parâmetro de servidor, calibrado para carro. Em vez de
 * impor esse valor, a comparação devolve o **ponto de equilíbrio** — o limiar em que a
 * escolha se inverte — e deixa o julgamento com o usuário. É o que se espera de um
 * sistema de apoio à decisão: apoiar a decisão, não substituí-la.
 */

/** Abaixo disso a diferença de percurso não é distinguível na prática. */
export const TOLERANCIA_KM = 0.05

export type RelacaoEntrePerfis =
  | 'identico'
  | 'domina'
  | 'dominado'
  | 'economiza-andando-mais'
  | 'poupa-percurso-pagando-mais'

export interface ComparacaoDePerfis {
  relacao: RelacaoEntrePerfis
  /** Diferenças do candidato em relação à referência; negativo significa "menos". */
  diferencaItensCentavos: number
  diferencaParadas: number
  diferencaKm: number
  /** O que muda ao trocar de perfil, em uma frase. */
  resumo: string
  /** O limiar em que a troca passa a compensar, quando existe troca. */
  pontoDeEquilibrio: string | null
}

function pluralizarParadas(quantidade: number): string {
  return quantidade === 1 ? '1 parada' : `${quantidade} paradas`
}

/** Descreve o esforço de deslocamento com as parcelas que de fato mudaram. */
function descreverEsforco(paradas: number, km: number): string {
  const partes: string[] = []
  if (paradas !== 0) partes.push(pluralizarParadas(Math.abs(paradas)))
  if (Math.abs(km) >= TOLERANCIA_KM) partes.push(formatarDistancia(Math.abs(km)))
  return partes.join(' e ')
}

/**
 * Monta a frase do limiar. Quando há diferença de percurso, o limiar é por quilômetro;
 * quando os perfis andam o mesmo e só mudam de paradas, é por parada.
 */
function montarPontoDeEquilibrio(
  economiaCentavos: number,
  paradas: number,
  km: number,
  sentido: 'menos' | 'mais'
): string | null {
  if (economiaCentavos <= 0) return null

  if (Math.abs(km) >= TOLERANCIA_KM) {
    const porKm = Math.round(economiaCentavos / Math.abs(km))
    return `Compensa se, para você, rodar 1 km custar ${sentido} de ${formatarReais(porKm)}.`
  }

  if (paradas !== 0) {
    const porParada = Math.round(economiaCentavos / Math.abs(paradas))
    return `Compensa se cada parada extra custar ${sentido} de ${formatarReais(porParada)}.`
  }

  return null
}

/**
 * Compara `candidato` com `referencia` — o perfil que o usuário escolheu.
 *
 * Args:
 *   referencia: o perfil atualmente exibido.
 *   candidato: o perfil alternativo sendo avaliado.
 *
 * Returns:
 *   A relação entre os dois, com o resumo e, quando há troca real entre economia e
 *   deslocamento, o ponto de equilíbrio.
 */
export function compararPerfis(
  referencia: Recomendacao,
  candidato: Recomendacao
): ComparacaoDePerfis {
  const diferencaItensCentavos = candidato.custo_itens_centavos - referencia.custo_itens_centavos
  const diferencaParadas =
    candidato.quantidade_mercados_visitados - referencia.quantidade_mercados_visitados
  const diferencaKm = candidato.distancia_total_km - referencia.distancia_total_km

  const base = { diferencaItensCentavos, diferencaParadas, diferencaKm }

  const mesmoPreco = diferencaItensCentavos === 0
  const mesmoPercurso = Math.abs(diferencaKm) < TOLERANCIA_KM && diferencaParadas === 0

  if (mesmoPreco && mesmoPercurso) {
    return {
      ...base,
      relacao: 'identico',
      resumo: 'Mesmo resultado do perfil escolhido.',
      pontoDeEquilibrio: null
    }
  }

  const andaMais = diferencaKm > TOLERANCIA_KM || diferencaParadas > 0
  const andaMenos = diferencaKm < -TOLERANCIA_KM || diferencaParadas < 0

  // Melhor nos dois critérios: não há troca a avaliar, logo não há limiar.
  if (diferencaItensCentavos <= 0 && !andaMais) {
    return {
      ...base,
      relacao: 'domina',
      resumo: 'Paga menos e anda menos: é melhor nos dois critérios.',
      pontoDeEquilibrio: null
    }
  }

  if (diferencaItensCentavos >= 0 && !andaMenos) {
    return {
      ...base,
      relacao: 'dominado',
      resumo: 'Paga mais e anda mais: não há vantagem em trocar.',
      pontoDeEquilibrio: null
    }
  }

  if (diferencaItensCentavos < 0) {
    const economia = -diferencaItensCentavos
    return {
      ...base,
      relacao: 'economiza-andando-mais',
      resumo:
        `Economiza ${formatarReais(economia)}, mas exige ` +
        `${descreverEsforco(diferencaParadas, diferencaKm)} a mais.`,
      pontoDeEquilibrio: montarPontoDeEquilibrio(
        economia,
        diferencaParadas,
        diferencaKm,
        'menos'
      )
    }
  }

  return {
    ...base,
    relacao: 'poupa-percurso-pagando-mais',
    resumo:
      `Custa ${formatarReais(diferencaItensCentavos)} a mais, mas poupa ` +
      `${descreverEsforco(diferencaParadas, diferencaKm)}.`,
    pontoDeEquilibrio: montarPontoDeEquilibrio(
      diferencaItensCentavos,
      diferencaParadas,
      diferencaKm,
      'mais'
    )
  }
}
