/**
 * Acesso tolerante ao `localStorage`: em modo privado ou com armazenamento bloqueado o app
 * continua funcionando, apenas sem persistência.
 */
export function lerJson<T>(chave: string): T | null {
  try {
    const bruto = localStorage.getItem(chave)
    return bruto ? (JSON.parse(bruto) as T) : null
  } catch {
    return null
  }
}

export function gravarJson(chave: string, valor: unknown): void {
  try {
    localStorage.setItem(chave, JSON.stringify(valor))
  } catch {
    /* silencioso por design */
  }
}

export function remover(chave: string): void {
  try {
    localStorage.removeItem(chave)
  } catch {
    /* silencioso por design */
  }
}
