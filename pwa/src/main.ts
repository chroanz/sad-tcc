import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { roteador } from './rotas/indice'
import { aoExpirarSessao } from './api/clienteHttp'
import { useSessaoStore } from './stores/sessao'
import './estilos/base.css'

const aplicacao = createApp(App)
aplicacao.use(createPinia())
aplicacao.use(roteador)

/**
 * Liga o cliente HTTP à sessão: qualquer resposta `NAO_AUTENTICADO` limpa o token e
 * devolve o usuário ao login, preservando o destino para retomar depois.
 *
 * Precisa ficar aqui, e não dentro da store, porque só depois de `use(createPinia())` é
 * possível instanciar uma store fora de um componente.
 */
aoExpirarSessao(() => {
  const sessao = useSessaoStore()
  sessao.encerrar()

  const atual = roteador.currentRoute.value
  if (atual.name !== 'entrar') {
    void roteador.push({ name: 'entrar', query: { retorno: atual.fullPath } })
  }
})

aplicacao.mount('#app')
