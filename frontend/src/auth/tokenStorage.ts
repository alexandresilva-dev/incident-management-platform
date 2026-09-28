// O token fica em localStorage: sobrevive a refrescar a página, mas está exposto se
// a app tiver uma vulnerabilidade XSS. A alternativa mais robusta são cookies
// HttpOnly, que pedem outro desenho no backend (CSRF, mesmo domínio).
const KEY = 'incident-platform.token'

// Se o localStorage não existir ou estiver bloqueado (modo privado, testes), guarda em memória.
let memoryToken: string | null = null

export function getToken(): string | null {
  try {
    return localStorage.getItem(KEY) ?? memoryToken
  } catch {
    return memoryToken
  }
}

export function setToken(token: string): void {
  memoryToken = token
  try {
    localStorage.setItem(KEY, token)
  } catch {
    // sem localStorage: fica só em memória
  }
}

export function clearToken(): void {
  memoryToken = null
  try {
    localStorage.removeItem(KEY)
  } catch {
    // nada a limpar
  }
}
