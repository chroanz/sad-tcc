import { requisitar } from './clienteHttp'
import type { CredenciaisEntrada, DadosCadastro, RespostaAutenticacao } from './tipos'

export function entrar(credenciais: CredenciaisEntrada): Promise<RespostaAutenticacao> {
  return requisitar<RespostaAutenticacao>('/auth/entrar', {
    metodo: 'POST',
    corpo: credenciais,
    publica: true
  })
}

export function registrar(dados: DadosCadastro): Promise<RespostaAutenticacao> {
  return requisitar<RespostaAutenticacao>('/auth/registrar', {
    metodo: 'POST',
    corpo: dados,
    publica: true
  })
}

export interface EstadoSaude {
  status: string
  banco: string
  otimizador: string
}

export function consultarSaude(): Promise<EstadoSaude> {
  return requisitar<EstadoSaude>('/saude', { publica: true })
}
