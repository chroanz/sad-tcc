import { onMounted, onUnmounted, ref, type Ref } from 'vue'

/** Estado reativo de conectividade, usado pelo aviso de offline e pelos botões de rede. */
export function usarEstadoDeConexao(): { online: Ref<boolean> } {
  const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine)

  const marcarOnline = (): void => {
    online.value = true
  }
  const marcarOffline = (): void => {
    online.value = false
  }

  onMounted(() => {
    window.addEventListener('online', marcarOnline)
    window.addEventListener('offline', marcarOffline)
  })

  onUnmounted(() => {
    window.removeEventListener('online', marcarOnline)
    window.removeEventListener('offline', marcarOffline)
  })

  return { online }
}
