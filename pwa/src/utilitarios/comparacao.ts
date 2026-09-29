import { formatarDistancia, formatarReais } from '@/utilitarios/formato'
import type { Recomendacao } from '@/api/tipos'

/**
 * Comparação entre dois perfis de compra, em linguagem de decisão.
 *
 * O SAD decide por preço e disponibilidade; a distância percorrida não é precificada. O
 * que separa os perfis é o que se paga no caixa contra quantos mercados se visita e quantos
 * quilômetros se anda. A comparação diz isso em termos concretos — "R$ 5,04 a mais no
 * caixa, em troca de 2 mercados em vez de 3" — e deixa o julgamento com o usuário, em vez
 * de impor um valor para a parada ou para o quilômetro.
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
  /**
   * Quanto cada mercado a mais (ou a menos) vale no caixa. Só existe quando a troca muda
   * duas paradas ou mais; com uma só, repetiria o valor do resumo.
   */
  pontoDeEquilibrio: string | null
}

function pluralizarMercados(quantidade: number): string {
  return quantidade === 1 ? '1 mercado' : `${quantidade} mercados`
}

/**
 * Descreve o esforço do candidato em relação à referência, com as parcelas que de fato
 * mudaram: "2 mercados em vez de 3 e 1,4 km a menos".
 */
function descreverEsforco(referencia: Recomendacao, candidato: Recomendacao, km: number): string {
  const partes: string[] = []
  if (candidato.quantidade_mercados_visitados !== referencia.quantidade_mercados_visitados) {
    partes.push(
      `${pluralizarMercados(candidato.quantidade_mercados_visitados)} em vez de ` +
        `${referencia.quantidade_mercados_visitados}`
    )
  }
  if (Math.abs(km) >= TOLERANCIA_KM) {
    partes.push(`${formatarDistancia(Math.abs(km))} a ${km > 0 ? 'mais' : 'menos'}`)
  }
  return partes.join(' e ')
}

/** Valor de cada mercado a mais ou a menos, quando a troca muda duas paradas ou mais. */
function valorPorMercado(
  diferencaCentavos: number,
  paradas: number,
  sentido: 'economiza' | 'custa'
): string | null {
  if (diferencaCentavos <= 0 || Math.abs(paradas) < 2) return null
  const porMercado = formatarReais(Math.round(diferencaCentavos / Math.abs(paradas)))
  return sentido === 'economiza'
    ? `Cada mercado a mais economiza, em média, ${porMercado}.`
    : `Cada mercado a menos custa, em média, ${porMercado}.`
}

/**
 * Compara `candidato` com `referencia` — o perfil que o usuário escolheu.
 *
 * Args:
 *   referencia: o perfil atualmente exibido.
 *   candidato: o perfil alternativo sendo avaliado.
 *
 * Returns:
 *   A relação entre os dois, com o resumo e, quando a troca muda várias paradas, o valor
 *   de cada mercado no caixa.
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
  const esforco = descreverEsforco(referencia, candidato, diferencaKm)

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

  // Melhor nos dois critérios: não há troca a avaliar.
  if (diferencaItensCentavos <= 0 && !andaMais) {
    const preco = mesmoPreco
      ? 'Mesmo valor no caixa'
      : `${formatarReais(-diferencaItensCentavos)} a menos no caixa`
    return {
      ...base,
      relacao: 'domina',
      resumo: esforco ? `${preco}, com ${esforco}.` : `${preco}.`,
      pontoDeEquilibrio: null
    }
  }

  if (diferencaItensCentavos >= 0 && !andaMenos) {
    const preco = mesmoPreco
      ? 'Mesmo valor no caixa'
      : `${formatarReais(diferencaItensCentavos)} a mais no caixa`
    return {
      ...base,
      relacao: 'dominado',
      resumo: esforco ? `${preco}, com ${esforco}: não compensa.` : `${preco}: não compensa.`,
      pontoDeEquilibrio: null
    }
  }

  if (diferencaItensCentavos < 0) {
    const economia = -diferencaItensCentavos
    return {
      ...base,
      relacao: 'economiza-andando-mais',
      resumo: `Economiza ${formatarReais(economia)} no caixa, mas com ${esforco}.`,
      pontoDeEquilibrio: valorPorMercado(economia, diferencaParadas, 'economiza')
    }
  }

  return {
    ...base,
    relacao: 'poupa-percurso-pagando-mais',
    resumo: `Paga ${formatarReais(diferencaItensCentavos)} a mais no caixa, em troca de ${esforco}.`,
    pontoDeEquilibrio: valorPorMercado(diferencaItensCentavos, diferencaParadas, 'custa')
  }
}
