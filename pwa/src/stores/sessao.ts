import { computed, ref, type ComputedRef, type Ref } from 'vue'
import { defineStore } from 'pinia'
import { entrar as entrarApi, registrar as registrarApi } from '@/api/autenticacao'
import { gravarToken, lerTokenArmazenado, mensagemAmigavel } from '@/api/clienteHttp'
import { gravarJson, lerJson, remover } from '@/utilitarios/armazenamento'
import type { CredenciaisEntrada, DadosCadastro, Usuario } from '@/api/tipos'

const CHAVE_USUARIO = 'sad-compras:usuario'

export interface RetornoSessaoStore {
  token: Ref<string | null>
  usuario: Ref<Usuario | null>
  carregando: Ref<boolean>
  erro: Ref<string | null>
  autenticado: ComputedRef<boolean>
  primeiroNome: ComputedRef<string>
  entrar: (credenciais: CredenciaisEntrada) => Promise<boolean>
  cadastrar: (dados: DadosCadastro) => Promise<boolean>
  encerrar: () => void
  limparErro: () => void
}

export const useSessaoStore = defineStore('sessao', (): RetornoSessaoStore => {
  const token = ref<string | null>(lerTokenArmazenado())
  const usuario = ref<Usuario | null>(lerJson<Usuario>(CHAVE_USUARIO))
  const carregando = ref(false)
  const erro = ref<string | null>(null)

  const autenticado = computed<boolean>(() => token.value !== null && token.value !== '')
  const primeiroNome = computed<string>(() => (usuario.value?.nome ?? '').split(' ')[0] ?? '')

  function aplicarSessao(novoToken: string, novoUsuario: Usuario): void {
    token.value = novoToken
    usuario.value = novoUsuario
    gravarToken(novoToken)
    gravarJson(CHAVE_USUARIO, novoUsuario)
  }

  function encerrar(): void {
    token.value = null
    usuario.value = null
    gravarToken(null)
    remover(CHAVE_USUARIO)
  }

  async function executarAutenticacao(
    acao: () => Promise<{ token: string; usuario: Usuario }>
  ): Promise<boolean> {
    carregando.value = true
    erro.value = null
    try {
      const resposta = await acao()
      aplicarSessao(resposta.token, resposta.usuario)
      return true
    } catch (falha) {
      erro.value = mensagemAmigavel(falha)
      return false
    } finally {
      carregando.value = false
    }
  }

  const entrar = (credenciais: CredenciaisEntrada): Promise<boolean> =>
    executarAutenticacao(() => entrarApi(credenciais))

  const cadastrar = (dados: DadosCadastro): Promise<boolean> =>
    executarAutenticacao(() => registrarApi(dados))

  function limparErro(): void {
    erro.value = null
  }

  return {
    token,
    usuario,
    carregando,
    erro,
    autenticado,
    primeiroNome,
    entrar,
    cadastrar,
    encerrar,
    limparErro
  }
})
