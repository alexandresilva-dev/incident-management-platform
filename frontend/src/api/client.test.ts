import { afterEach, describe, expect, it, vi } from 'vitest'
import { clearToken, getToken, setToken } from '../auth/tokenStorage.ts'
import { api, ApiError, formatErrorDetail, setUnauthorizedHandler, toQuery } from './client.ts'

afterEach(() => {
  vi.unstubAllGlobals()
  clearToken()
  setUnauthorizedHandler(undefined)
})

function stubFetch(response: Response | Error) {
  const fetchMock = vi.fn((_url: string, _init?: RequestInit) =>
    response instanceof Error ? Promise.reject(response) : Promise.resolve(response),
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

describe('formatErrorDetail', () => {
  it('returns plain string details untouched', () => {
    expect(formatErrorDetail('Incident 5 not found')).toBe('Incident 5 not found')
  })

  it('formats FastAPI validation errors, dropping the "body" prefix', () => {
    const detail = [
      { loc: ['body', 'title'], msg: 'String should have at least 1 character' },
      { loc: ['body', 'asset_ids', 0], msg: 'Input should be a valid integer' },
    ]
    expect(formatErrorDetail(detail)).toBe(
      'title: String should have at least 1 character; asset_ids.0: Input should be a valid integer',
    )
  })

  it('falls back to a generic message for unknown shapes', () => {
    expect(formatErrorDetail(undefined)).toBe('Unexpected error')
  })
})

describe('toQuery', () => {
  it('skips empty values and encodes the rest', () => {
    expect(toQuery({ status: 'open', q: '', severity: undefined, skip: 0, limit: 20 })).toBe(
      '?status=open&skip=0&limit=20',
    )
    expect(toQuery({ q: 'a&b' })).toBe('?q=a%26b')
  })

  it('returns an empty string when there is nothing to send', () => {
    expect(toQuery({})).toBe('')
  })
})

describe('api requests', () => {
  it('builds the URL from the filters and returns the parsed body', async () => {
    const fetchMock = stubFetch(json([{ id: 1 }]))

    const result = await api.listIncidents({ status: 'open', sort: 'priority' })

    expect(result).toEqual([{ id: 1 }])
    expect(fetchMock.mock.calls[0]?.[0]).toBe('http://localhost:8000/incidents?status=open&sort=priority')
  })

  it('sends transitions as JSON and omits an empty comment', async () => {
    const fetchMock = stubFetch(json({ id: 1, status: 'investigating' }))

    await api.transitionIncident(1, 'investigating', '')

    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toContain('/incidents/1/transitions')
    expect(init?.method).toBe('POST')
    expect(JSON.parse(init?.body as string)).toEqual({ to_status: 'investigating' })
  })

  it('turns an API error into an ApiError with the status and message', async () => {
    stubFetch(json({ detail: 'Cannot move incident from open to closed' }, 409))

    const error = await api.transitionIncident(1, 'closed').catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(409)
    expect((error as ApiError).message).toBe('Cannot move incident from open to closed')
  })

  it('reports an unreachable backend as status 0', async () => {
    stubFetch(new TypeError('Failed to fetch'))

    const error = await api.getDashboardSummary().catch((e: unknown) => e)

    expect((error as ApiError).status).toBe(0)
    expect((error as ApiError).message).toMatch(/Cannot reach the API/)
  })

  it('handles error bodies that are not JSON', async () => {
    stubFetch(new Response('Bad gateway', { status: 502, statusText: 'Bad Gateway' }))

    const error = await api.getDashboardSummary().catch((e: unknown) => e)

    expect((error as ApiError).status).toBe(502)
    expect((error as ApiError).message).toBe('Bad Gateway')
  })
})

describe('authentication', () => {
  it('sends the stored token as a Bearer header', async () => {
    setToken('abc123')
    const fetchMock = stubFetch(json({ id: 1 }))

    await api.me()

    const init = fetchMock.mock.calls[0]![1]!
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer abc123')
  })

  it('sends no Authorization header when there is no token', async () => {
    const fetchMock = stubFetch(json({ id: 1 }))

    await api.me()

    const init = fetchMock.mock.calls[0]![1]!
    expect(init.headers).not.toHaveProperty('Authorization')
  })

  it('logs in with an OAuth2 form body (username is the email)', async () => {
    const fetchMock = stubFetch(json({ access_token: 't', token_type: 'bearer' }))

    await api.login('ana@example.com', 'pw')

    const [url, init] = fetchMock.mock.calls[0]! as [string, RequestInit]
    const body = init.body as URLSearchParams
    expect(url).toMatch(/\/auth\/login$/)
    expect(init.method).toBe('POST')
    expect((init.headers as Record<string, string>)['Content-Type']).toBe(
      'application/x-www-form-urlencoded',
    )
    expect(body.get('username')).toBe('ana@example.com')
    expect(body.get('password')).toBe('pw')
  })

  it('drops the token and notifies the app when the API answers 401', async () => {
    setToken('expired')
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)
    stubFetch(json({ detail: 'Invalid or expired token' }, 401))

    await expect(api.getDashboardSummary()).rejects.toBeInstanceOf(ApiError)

    expect(getToken()).toBeNull()
    expect(onUnauthorized).toHaveBeenCalledOnce()
  })

  it('treats a 401 on login as wrong credentials, not as an expired session', async () => {
    setToken('still-valid')
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)
    stubFetch(json({ detail: 'Incorrect email or password' }, 401))

    const error = await api.login('a@b.c', 'wrong').catch((e: unknown) => e)

    expect((error as ApiError).message).toBe('Incorrect email or password')
    expect(onUnauthorized).not.toHaveBeenCalled()
    expect(getToken()).toBe('still-valid')
  })
})
