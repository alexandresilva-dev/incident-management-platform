import { clearToken, getToken } from '../auth/tokenStorage.ts'
import type {
  Asset,
  DashboardSummary,
  Incident,
  IncidentCreate,
  IncidentFilters,
  IncidentStatus,
  IncidentSummary,
  IncidentUpdate,
  StatusHistoryEntry,
  Token,
  User,
  Vulnerability,
} from './types.ts'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** O FastAPI devolve `detail` como texto (erros de negócio) ou como lista (422 de validação). */
export function formatErrorDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item: unknown) => {
        if (item && typeof item === 'object' && 'msg' in item) {
          const { msg, loc } = item as { msg: unknown; loc?: unknown }
          const field = Array.isArray(loc) ? loc.filter((part) => part !== 'body').join('.') : ''
          return field ? `${field}: ${String(msg)}` : String(msg)
        }
        return JSON.stringify(item)
      })
      .join('; ')
  }
  return 'Unexpected error'
}

export function toQuery(params: object): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  }
  const query = search.toString()
  return query ? `?${query}` : ''
}

let unauthorizedHandler: (() => void) | undefined

/** Chamado quando a API responde 401 a um pedido autenticado (token expirado/inválido). */
export function setUnauthorizedHandler(handler: (() => void) | undefined): void {
  unauthorizedHandler = handler
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  { handleUnauthorized = true } = {},
): Promise<T> {
  const token = getToken()
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the API. Is the backend running?')
  }

  if (!response.ok) {
    if (response.status === 401 && handleUnauthorized) {
      // Sessão inválida: esquece o token e avisa a app (que mostra o login).
      clearToken()
      unauthorizedHandler?.()
    }
    const body: unknown = await response.json().catch(() => undefined)
    const detail =
      body && typeof body === 'object' && 'detail' in body ? body.detail : response.statusText
    throw new ApiError(response.status, formatErrorDetail(detail))
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

const jsonBody = (data: unknown): RequestInit => ({ body: JSON.stringify(data) })

export const api = {
  // O login segue o standard OAuth2 do FastAPI: formulário com "username" (o email) e
  // "password". Um 401 aqui é "credenciais erradas", não "sessão expirada".
  login: (email: string, password: string) =>
    request<Token>(
      '/auth/login',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: email, password }),
      },
      { handleUnauthorized: false },
    ),
  me: () => request<User>('/auth/me'),

  getDashboardSummary: () => request<DashboardSummary>('/dashboard/summary'),

  listIncidents: (filters: IncidentFilters = {}) =>
    request<IncidentSummary[]>(`/incidents${toQuery(filters)}`),
  getIncident: (id: number) => request<Incident>(`/incidents/${id}`),
  createIncident: (data: IncidentCreate) =>
    request<Incident>('/incidents', { method: 'POST', ...jsonBody(data) }),
  updateIncident: (id: number, data: IncidentUpdate) =>
    request<Incident>(`/incidents/${id}`, { method: 'PATCH', ...jsonBody(data) }),
  transitionIncident: (id: number, to_status: IncidentStatus, comment?: string) =>
    request<Incident>(`/incidents/${id}/transitions`, {
      method: 'POST',
      ...jsonBody({ to_status, comment: comment || undefined }),
    }),
  getIncidentHistory: (id: number) => request<StatusHistoryEntry[]>(`/incidents/${id}/history`),

  listAssets: () => request<Asset[]>('/assets?limit=200'),
  listVulnerabilities: () => request<Vulnerability[]>('/vulnerabilities?limit=200'),
}
