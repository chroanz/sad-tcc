import type { CodigoErro, EnvelopeErro } from './tipos'

const URL_BASE: string =
  (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8080/api/v1'

const CHAVE_TOKEN = 'sad-compras:token'

/** Erro normalizado: toda falha de rede ou de API chega às telas neste formato. */
export class ErroApi extends Error {
  readonly codigo: CodigoErro
  readonly status: number
  readonly detalhes: unknown

  constructor(codigo: CodigoErro, mensagem: string, status = 0, detalhes: unknown = null) {
    super(mensagem)
    this.name = 'ErroApi'
    this.codigo = codigo
    this.status = status
    this.detalhes = detalhes
  }
}

export function lerTokenArmazenado(): string | null {
  try {
    return localStorage.getItem(CHAVE_TOKEN)
  } catch {
    return null
  }
}

export function gravarToken(token: string | null): void {
  try {
    if (token === null) localStorage.removeItem(CHAVE_TOKEN)
    else localStorage.setItem(CHAVE_TOKEN, token)
  } catch {
    /* modo privado do navegador: a sessão simplesmente não persiste */
  }
}

type OuvinteSessaoExpirada = () => void
const ouvintesSessaoExpirada: OuvinteSessaoExpirada[] = []

/**
 * Registra um callback disparado sempre que a API devolve `NAO_AUTENTICADO`.
 * A store de sessão usa isso para limpar o token e voltar ao login.
 */
export function aoExpirarSessao(ouvinte: OuvinteSessaoExpirada): void {
  ouvintesSessaoExpirada.push(ouvinte)
}

const MENSAGENS_PADRAO: Record<CodigoErro, string> = {
  VALIDACAO: 'Os dados enviados não foram aceitos.',
  NAO_AUTENTICADO: 'Sua sessão expirou. Entre novamente.',
  NAO_AUTORIZADO: 'Este conteúdo pertence a outro usuário.',
  NAO_ENCONTRADO: 'Não encontramos o que você procura.',
  CONFLITO: 'Já existe um registro com esses dados.',
  OTIMIZADOR_INDISPONIVEL:
    'O serviço de otimização está indisponível no momento. Tente novamente em instantes.',
  ERRO_INTERNO: 'O servidor encontrou um problema inesperado. Tente novamente.',
  SEM_CONEXAO: 'Não foi possível falar com o servidor. Verifique sua conexão e tente de novo.',
  RESPOSTA_INVALIDA: 'O servidor respondeu em um formato inesperado.'
}

const CODIGOS_CONHECIDOS = new Set<string>(Object.keys(MENSAGENS_PADRAO))

function codigoPorStatus(status: number): CodigoErro {
  switch (status) {
    case 400:
      return 'VALIDACAO'
    case 401:
      return 'NAO_AUTENTICADO'
    case 403:
      return 'NAO_AUTORIZADO'
    case 404:
      return 'NAO_ENCONTRADO'
    case 409:
      return 'CONFLITO'
    case 503:
      return 'OTIMIZADOR_INDISPONIVEL'
    default:
      return 'ERRO_INTERNO'
  }
}

function ehEnvelopeErro(corpo: unknown): corpo is EnvelopeErro {
  return (
    typeof corpo === 'object' &&
    corpo !== null &&
    'erro' in corpo &&
    typeof (corpo as { erro: unknown }).erro === 'object' &&
    (corpo as { erro: unknown }).erro !== null
  )
}

async function interpretarFalha(resposta: Response): Promise<ErroApi> {
  let corpo: unknown = null
  try {
    corpo = await resposta.json()
  } catch {
    corpo = null
  }

  if (ehEnvelopeErro(corpo)) {
    const { codigo, mensagem, detalhes } = corpo.erro
    const codigoNormalizado: CodigoErro = CODIGOS_CONHECIDOS.has(codigo)
      ? codigo
      : codigoPorStatus(resposta.status)
    return new ErroApi(
      codigoNormalizado,
      mensagem?.trim() || MENSAGENS_PADRAO[codigoNormalizado],
      resposta.status,
      detalhes ?? null
    )
  }

  const codigo = codigoPorStatus(resposta.status)
  return new ErroApi(codigo, MENSAGENS_PADRAO[codigo], resposta.status)
}

interface OpcoesRequisicao {
  metodo?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  corpo?: unknown
  parametros?: Record<string, string | number | boolean | undefined>
  sinal?: AbortSignal
  /** Rotas públicas (`/auth/*`, `/saude`) não enviam o cabeçalho Authorization. */
  publica?: boolean
}

function montarUrl(caminho: string, parametros?: OpcoesRequisicao['parametros']): string {
  const url = `${URL_BASE.replace(/\/$/, '')}${caminho}`
  if (!parametros) return url
  const busca = new URLSearchParams()
  for (const [chave, valor] of Object.entries(parametros)) {
    if (valor === undefined || valor === '') continue
    busca.set(chave, String(valor))
  }
  const consulta = busca.toString()
  return consulta ? `${url}?${consulta}` : url
}

/** Executa a requisição e devolve o corpo já tipado, ou lança `ErroApi`. */
export async function requisitar<T>(caminho: string, opcoes: OpcoesRequisicao = {}): Promise<T> {
  const { metodo = 'GET', corpo, parametros, sinal, publica = false } = opcoes

  const cabecalhos: Record<string, string> = { Accept: 'application/json' }
  if (corpo !== undefined) cabecalhos['Content-Type'] = 'application/json'
  if (!publica) {
    const token = lerTokenArmazenado()
    if (token) cabecalhos.Authorization = `Bearer ${token}`
  }

  let resposta: Response
  try {
    resposta = await fetch(montarUrl(caminho, parametros), {
      method: metodo,
      headers: cabecalhos,
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
      signal: sinal
    })
  } catch {
    throw new ErroApi(
      'SEM_CONEXAO',
      navigator.onLine
        ? MENSAGENS_PADRAO.SEM_CONEXAO
        : 'Você está sem internet. Reconecte para continuar.',
      0
    )
  }

  if (!resposta.ok) {
    const erro = await interpretarFalha(resposta)
    if (erro.codigo === 'NAO_AUTENTICADO') {
      for (const ouvinte of ouvintesSessaoExpirada) ouvinte()
    }
    throw erro
  }

  if (resposta.status === 204) return undefined as T

  const texto = await resposta.text()
  if (!texto) return undefined as T
  try {
    return JSON.parse(texto) as T
  } catch {
    throw new ErroApi('RESPOSTA_INVALIDA', MENSAGENS_PADRAO.RESPOSTA_INVALIDA, resposta.status)
  }
}

/**
 * Coleções: o contrato mostra apenas o formato dos objetos, sem fixar se a resposta é um
 * array puro ou um envelope. Aceitamos as duas formas para não quebrar com o servidor real.
 */
export function extrairLista<T>(corpo: unknown): T[] {
  if (Array.isArray(corpo)) return corpo as T[]
  if (typeof corpo === 'object' && corpo !== null) {
    for (const chave of ['dados', 'itens', 'resultados', 'lista', 'registros']) {
      const valor = (corpo as Record<string, unknown>)[chave]
      if (Array.isArray(valor)) return valor as T[]
    }
  }
  return []
}

export function mensagemAmigavel(erro: unknown): string {
  if (erro instanceof ErroApi) return erro.message
  if (erro instanceof Error && erro.message) return erro.message
  return 'Algo deu errado. Tente novamente.'
}

export const urlBaseApi = URL_BASE
