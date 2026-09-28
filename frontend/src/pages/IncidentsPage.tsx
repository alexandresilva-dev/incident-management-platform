import { useCallback, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router'
import { api } from '../api/client.ts'
import {
  INCIDENT_CATEGORIES,
  INCIDENT_STATUSES,
  PRIORITIES,
  SEVERITIES,
  type IncidentFilters,
} from '../api/types.ts'
import { PriorityBadge, SeverityBadge, StatusBadge } from '../components/Badges.tsx'
import { ErrorMessage, Loading } from '../components/StateViews.tsx'
import { useApi } from '../hooks/useApi.ts'
import { formatDateTime, humanize } from '../lib/format.ts'

const PAGE_SIZE = 15

/** Só aceita valores válidos vindos do URL (o utilizador pode escrever o que quiser). */
function pick<T extends string>(value: string | null, allowed: readonly T[]): T | undefined {
  return allowed.find((option) => option === value)
}

function readFilters(params: URLSearchParams): IncidentFilters {
  return {
    status: pick(params.get('status'), INCIDENT_STATUSES),
    severity: pick(params.get('severity'), SEVERITIES),
    priority: pick(params.get('priority'), PRIORITIES),
    category: pick(params.get('category'), INCIDENT_CATEGORIES),
    q: params.get('q') ?? undefined,
    sort: params.get('sort') === 'newest' ? 'newest' : 'priority',
  }
}

function readPage(params: URLSearchParams): number {
  return Math.max(1, Number(params.get('page')) || 1)
}

export default function IncidentsPage() {
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState(params.get('q') ?? '')

  const page = readPage(params)
  const filters = readFilters(params)

  const load = useCallback(
    () =>
      api.listIncidents({
        ...readFilters(params),
        skip: (readPage(params) - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
    [params],
  )
  const { data, error, loading, reload } = useApi(load)

  function updateParam(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    next.delete('page') // qualquer filtro novo volta à primeira página
    setParams(next)
  }

  function goToPage(target: number) {
    const next = new URLSearchParams(params)
    next.set('page', String(target))
    setParams(next)
  }

  function submitSearch(event: FormEvent) {
    event.preventDefault()
    updateParam('q', search.trim())
  }

  return (
    <>
      <div className="page-header">
        <h1>Incidents</h1>
        <Link to="/incidents/new" className="btn btn--primary">New incident</Link>
      </div>

      <form className="filters" onSubmit={submitSearch}>
        <input
          type="search"
          placeholder="Search title…"
          aria-label="Search title"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <FilterSelect label="Status" value={params.get('status')} options={INCIDENT_STATUSES} onChange={(v) => updateParam('status', v)} />
        <FilterSelect label="Priority" value={params.get('priority')} options={PRIORITIES} onChange={(v) => updateParam('priority', v)} />
        <FilterSelect label="Severity" value={params.get('severity')} options={SEVERITIES} onChange={(v) => updateParam('severity', v)} />
        <FilterSelect label="Category" value={params.get('category')} options={INCIDENT_CATEGORIES} onChange={(v) => updateParam('category', v)} />
        <select
          aria-label="Sort"
          value={filters.sort}
          onChange={(event) => updateParam('sort', event.target.value)}
        >
          <option value="priority">Sort: priority</option>
          <option value="newest">Sort: newest</option>
        </select>
      </form>

      {error && <ErrorMessage message={error} onRetry={reload} />}
      {!data && loading && <Loading />}

      {data && (
        <>
          {data.length === 0 ? (
            <p className="empty">No incidents match these filters.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Priority</th>
                    <th>Title</th>
                    <th>Category</th>
                    <th>Severity</th>
                    <th>Status</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((incident) => (
                    <tr key={incident.id}>
                      <td><PriorityBadge value={incident.priority} /></td>
                      <td><Link to={`/incidents/${incident.id}`}>{incident.title}</Link></td>
                      <td>{humanize(incident.category)}</td>
                      <td><SeverityBadge value={incident.severity} /></td>
                      <td><StatusBadge value={incident.status} /></td>
                      <td className="nowrap">{formatDateTime(incident.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="pagination">
            <button className="btn btn--small" disabled={page === 1} onClick={() => goToPage(page - 1)}>
              Previous
            </button>
            <span className="muted">Page {page}</span>
            <button className="btn btn--small" disabled={data.length < PAGE_SIZE} onClick={() => goToPage(page + 1)}>
              Next
            </button>
          </div>
        </>
      )}
    </>
  )
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string | null
  options: readonly string[]
  onChange: (value: string) => void
}) {
  return (
    <select aria-label={label} value={value ?? ''} onChange={(event) => onChange(event.target.value)}>
      <option value="">{label}: all</option>
      {options.map((option) => (
        <option key={option} value={option}>
          {humanize(option)}
        </option>
      ))}
    </select>
  )
}
