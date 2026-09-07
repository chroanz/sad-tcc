import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useSessaoStore } from '@/stores/sessao'

/**
 * `requerSessao` na meta é o que o guarda global consulta. Marcar a rota é mais seguro
 * do que listar exceções: uma tela nova nasce protegida por padrão.
 */
const rotas: RouteRecordRaw[] = [
  {
    path: '/entrar',
    name: 'entrar',
    component: () => import('@/telas/TelaEntrar.vue'),
    meta: { requerSessao: false, titulo: 'Entrar' }
  },
  {
    path: '/',
    name: 'listas',
    component: () => import('@/telas/TelaMinhasListas.vue'),
    meta: { requerSessao: true, titulo: 'Minhas listas' }
  },
  {
    path: '/listas/:id',
    name: 'editor-lista',
    component: () => import('@/telas/TelaEditorDeLista.vue'),
    props: true,
    meta: { requerSessao: true, titulo: 'Editar lista' }
  },
  {
    path: '/listas/:id/resultado',
    name: 'resultado',
    component: () => import('@/telas/TelaResultado.vue'),
    props: true,
    meta: { requerSessao: true, titulo: 'Recomendação' }
  },
  {
    path: '/listas/:id/historico',
    name: 'historico',
    component: () => import('@/telas/TelaHistorico.vue'),
    props: true,
    meta: { requerSessao: true, titulo: 'Histórico' }
  },
  {
    path: '/mercados',
    name: 'mercados',
    component: () => import('@/telas/TelaMercados.vue'),
    meta: { requerSessao: true, titulo: 'Mercados' }
  },
  {
    path: '/:caminho(.*)*',
    name: 'nao-encontrado',
    redirect: { name: 'listas' }
  }
]

export const roteador = createRouter({
  history: createWebHistory(),
  routes: rotas,
  scrollBehavior: () => ({ top: 0 })
})

roteador.beforeEach((destino) => {
  const sessao = useSessaoStore()

  if (destino.meta.requerSessao && !sessao.autenticado) {
    return { name: 'entrar', query: { retorno: destino.fullPath } }
  }
  if (destino.name === 'entrar' && sessao.autenticado) {
    return { name: 'listas' }
  }
  return true
})

roteador.afterEach((destino) => {
  const titulo = destino.meta.titulo as string | undefined
  document.title = titulo ? `${titulo} · Compra Certa` : 'Compra Certa'
})
