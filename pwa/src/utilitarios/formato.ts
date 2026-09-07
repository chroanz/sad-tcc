const FORMATADOR_REAIS = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

const FORMATADOR_PERCENTUAL = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1
})

const FORMATADOR_DATA = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit'
})

/**
 * Dinheiro trafega em centavos inteiros; a divisão por 100 acontece só na apresentação,
 * nunca em cálculo (RNF15).
 */
export function formatarReais(centavos: number): string {
  if (!Number.isFinite(centavos)) return FORMATADOR_REAIS.format(0)
  return FORMATADOR_REAIS.format(Math.trunc(centavos) / 100)
}

export function formatarPercentual(valor: number): string {
  if (!Number.isFinite(valor)) return '0,0%'
  return `${FORMATADOR_PERCENTUAL.format(valor)}%`
}

export function formatarDistancia(km: number): string {
  if (!Number.isFinite(km)) return '—'
  if (km < 1) return `${Math.round(km * 1000)} m`
  return `${FORMATADOR_PERCENTUAL.format(km)} km`
}

export function formatarDataHora(iso: string | undefined): string {
  if (!iso) return '—'
  const data = new Date(iso)
  if (Number.isNaN(data.getTime())) return '—'
  return FORMATADOR_DATA.format(data)
}

export function formatarQuantidade(quantidade: number, unidade: string): string {
  const numero = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 3 }).format(quantidade)
  return `${numero} ${unidade}`
}

export function formatarCoordenada(valor: number): string {
  if (!Number.isFinite(valor)) return '—'
  return valor.toFixed(6).replace('.', ',')
}

const MOTIVOS: Record<string, string> = {
  SEM_CANDIDATO_COM_ESTOQUE: 'Nenhum mercado tem esse item com estoque suficiente.',
  SEM_PRECO_CADASTRADO: 'Nenhum mercado tem preço cadastrado para esse item.',
  SEM_PRECO: 'Nenhum mercado tem preço cadastrado para esse item.',
  ESTOQUE_INSUFICIENTE: 'Os mercados têm o item, mas não na quantidade pedida.',
  SEM_CANDIDATO: 'Nenhum mercado disponível pode atender esse item.'
}

/** Traduz o código técnico de `itens_nao_atendidos` para linguagem do usuário final. */
export function explicarMotivo(motivo: string): string {
  const chave = (motivo ?? '').toUpperCase()
  if (MOTIVOS[chave]) return MOTIVOS[chave]
  if (!motivo) return 'Não foi possível atender esse item.'
  // Fallback: transforma UM_CODIGO_ASSIM em uma frase legível.
  return `${motivo.replace(/_/g, ' ').toLowerCase().replace(/^./, (c) => c.toUpperCase())}.`
}

const STATUS_SOLVER: Record<string, string> = {
  OTIMO: 'Solução ótima comprovada',
  OPTIMAL: 'Solução ótima comprovada',
  VIAVEL: 'Solução viável (não comprovadamente ótima)',
  FEASIBLE: 'Solução viável (não comprovadamente ótima)',
  INVIAVEL: 'Nenhuma solução viável encontrada',
  INFEASIBLE: 'Nenhuma solução viável encontrada'
}

export function explicarStatus(status: string): string {
  return STATUS_SOLVER[(status ?? '').toUpperCase()] ?? status ?? '—'
}
