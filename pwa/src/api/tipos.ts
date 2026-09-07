/**
 * Tipos que espelham o contrato em `docs/contrato-api-rest.md`.
 * Os nomes dos campos seguem exatamente o JSON da API (português) e não devem ser
 * renomeados aqui.
 */

export type CodigoErro =
  | 'VALIDACAO'
  | 'NAO_AUTENTICADO'
  | 'NAO_AUTORIZADO'
  | 'NAO_ENCONTRADO'
  | 'CONFLITO'
  | 'OTIMIZADOR_INDISPONIVEL'
  | 'ERRO_INTERNO'
  | 'SEM_CONEXAO'
  | 'RESPOSTA_INVALIDA'

export interface EnvelopeErro {
  erro: {
    codigo: CodigoErro
    mensagem: string
    detalhes?: unknown
  }
}

/* ---------- Autenticação ---------- */

export interface Usuario {
  id: number
  nome: string
  email: string
}

export interface RespostaAutenticacao {
  token: string
  usuario: Usuario
}

export interface CredenciaisEntrada {
  email: string
  senha: string
}

export interface DadosCadastro extends CredenciaisEntrada {
  nome: string
}

/* ---------- Catálogo ---------- */

export interface Produto {
  id: number
  nome: string
  categoria: string
}

export interface Marca {
  id: number
  produto_id: number
  nome: string
}

export interface Mercado {
  id: number
  nome: string
  latitude: number
  longitude: number
  endereco: string
}

/* ---------- Listas ---------- */

export interface ListaResumo {
  id: number
  nome: string
  criado_em?: string
  /** Contagem devolvida por `GET /listas`; o nome do campo pode variar, ver `normalizarLista`. */
  quantidade_itens?: number
}

export interface ItemLista {
  id: number
  lista_id?: number
  produto_id: number
  produto_nome?: string
  marca_id: number | null
  marca_nome?: string | null
  quantidade: number
  unidade: string
}

export interface ListaDetalhada extends ListaResumo {
  itens: ItemLista[]
}

export interface EntradaItemLista {
  produto_id: number
  marca_id: number | null
  quantidade: number
  unidade: string
}

/* ---------- Recomendação ---------- */

export type PerfilConveniencia = 'economico' | 'equilibrado' | 'conveniente'

export interface Origem {
  latitude: number
  longitude: number
}

export interface PedidoRecomendacao {
  perfil: PerfilConveniencia
  origem?: Origem
  peso_conveniencia?: number
  /** Recorte dos mercados candidatos, em km a partir da origem. Ausente: sem recorte. */
  raio_km?: number
}

export interface ParadaRota {
  ordem: number
  mercado_id: number
  nome: string
  distancia_do_anterior_km: number
}

export interface ItemComprado {
  item_id: number
  produto_nome: string
  marca_nome: string | null
  quantidade: number
  unidade: string
  preco_unitario_centavos: number
  custo_centavos: number
}

export interface CompraNoMercado {
  mercado_id: number
  nome: string
  endereco: string
  subtotal_centavos: number
  itens: ItemComprado[]
}

export interface ItemNaoAtendido {
  item_id: number
  produto_nome: string
  motivo: string
}

export interface EconomiaEstimada {
  mercado_unico_id?: number | null
  mercado_unico_nome: string | null
  custo_mercado_unico_centavos: number | null
  economia_centavos: number | null
  economia_percentual: number | null
  /** Quantos itens entraram na comparação; ver "Baseline de economia" no contrato. */
  itens_comparados?: number
  /** Verdadeiro quando nenhum mercado atende sozinho a lista inteira. */
  comparacao_parcial?: boolean
  observacao: string | null
}

export interface Recomendacao {
  id: number
  lista_id: number
  gerado_em: string
  perfil: PerfilConveniencia
  peso_conveniencia: number
  origem_aproximada: boolean
  raio_km?: number | null
  mercados_considerados?: number
  status: string
  custo_itens_centavos: number
  custo_logistico_centavos: number
  custo_total_centavos: number
  /**
   * Parâmetros que produziram `custo_logistico_centavos`. Ausentes (0) em recomendações
   * gravadas antes de o contrato passar a ecoá-los.
   */
  custo_por_visita_centavos?: number
  custo_por_km_centavos?: number
  quantidade_mercados_visitados: number
  distancia_total_km: number
  rota: ParadaRota[]
  compras_por_mercado: CompraNoMercado[]
  itens_nao_atendidos: ItemNaoAtendido[]
  economia: EconomiaEstimada | null
}

/** Item do histórico: subconjunto resumido de `Recomendacao`. */
export interface RecomendacaoResumo {
  id: number
  lista_id?: number
  gerado_em: string
  perfil: PerfilConveniencia
  peso_conveniencia?: number
  status?: string
  custo_total_centavos: number
  quantidade_mercados_visitados?: number
}
