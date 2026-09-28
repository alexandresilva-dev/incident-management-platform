import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, setUnauthorizedHandler } from '../api/client.ts'
import { AuthContext, type AuthState } from './AuthContext.ts'
import { clearToken, getToken, setToken } from './tokenStorage.ts'

const ANONYMOUS: AuthState = { status: 'anonymous', user: null }

export function AuthProvider({ children }: { children: ReactNode }) {
  // Se há um token guardado, ainda não sabemos se é válido: pergunta-se à API.
  const [state, setState] = useState<AuthState>(
    getToken() ? { status: 'loading', user: null } : ANONYMOUS,
  )

  useEffect(() => {
    // Qualquer 401 vindo da API (token expirado) termina a sessão.
    setUnauthorizedHandler(() => setState(ANONYMOUS))
    return () => setUnauthorizedHandler(undefined)
  }, [])

  useEffect(() => {
    if (!getToken()) return
    api
      .me()
      .then((user) => setState({ status: 'authenticated', user }))
      .catch(() => {
        clearToken()
        setState(ANONYMOUS)
      })
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await api.login(email, password)
    setToken(access_token)
    const user = await api.me()
    setState({ status: 'authenticated', user })
  }, [])

  const logout = useCallback(() => {
    clearToken()
    setState(ANONYMOUS)
  }, [])

  const value = useMemo(() => ({ ...state, login, logout }), [state, login, logout])
  return <AuthContext value={value}>{children}</AuthContext>
}
