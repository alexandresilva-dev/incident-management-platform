import { useCallback, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import { api } from '../api/client.ts'
import {
  INCIDENT_CATEGORIES,
  SEVERITIES,
  type Incident,
  type IncidentCategory,
  type IncidentStatus,
  type Severity,
} from '../api/types.ts'
import { PriorityBadge, SeverityBadge, StatusBadge } from '../components/Badges.tsx'
import { ErrorMessage, Loading } from '../components/StateViews.tsx'
import { useApi } from '../hooks/useApi.ts'
import { formatDateTime, humanize } from '../lib/format.ts'
import { transitionLabel } from '../lib/workflow.ts'

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

export default function IncidentDetailPage() {
  const { id: idParam } = useParams()
  const id = Number(idParam)
  const validId = Number.isInteger(id) && id > 0

  const load = useCallback(
    () =>
      validId
        ? Promise.all([api.getIncident(id), api.getIncidentHistory(id)])
        : Promise.reject(new Error('Invalid incident id')),
    [id, validId],
  )
  const { data, error, reload } = useApi(load)

  if (error) return <ErrorMessage message={error} onRetry={reload} />
  // Ao recarregar (após uma transição) mantém-se o conteúdo atual em vez de piscar;
  // só se mostra "Loading" enquanto não há dados DESTE incidente (ex.: ao navegar de um para outro).
  if (!data || data[0].id !== id) return <Loading />

  const [incident, history] = data

  return (
    <>
      <p>
        <Link to="/incidents">← All incidents</Link>
      </p>

      <div className="page-header">
        <h1>{incident.title}</h1>
        <div className="badges">
          <PriorityBadge value={incident.priority} />
          <SeverityBadge value={incident.severity} />
          <StatusBadge value={incident.status} />
        </div>
      </div>

      <dl className="meta">
        <div><dt>Category</dt><dd>{humanize(incident.category)}</dd></div>
        <div><dt>Created</dt><dd>{formatDateTime(incident.created_at)}</dd></div>
        <div><dt>Last update</dt><dd>{formatDateTime(incident.updated_at)}</dd></div>
        {incident.resolved_at && <div><dt>Resolved</dt><dd>{formatDateTime(incident.resolved_at)}</dd></div>}
        {incident.closed_at && <div><dt>Closed</dt><dd>{formatDateTime(incident.closed_at)}</dd></div>}
      </dl>

      <div className="columns">
        <div className="stack">
          <section className="card">
            <h2>Description</h2>
            <p className={incident.description ? undefined : 'muted'}>
              {incident.description ?? 'No description provided.'}
            </p>
          </section>

          <section className="card">
            <h2>Affected assets</h2>
            {incident.assets.length === 0 ? (
              <p className="muted">No assets linked.</p>
            ) : (
              <ul className="list">
                {incident.assets.map((asset) => (
                  <li key={asset.id}>
                    <strong>{asset.name}</strong>
                    <span className="muted"> · {humanize(asset.asset_type)}</span>
                    <span className="list__aside">
                      criticality <SeverityBadge value={asset.criticality} />
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card">
            <h2>Vulnerabilities</h2>
            {incident.vulnerabilities.length === 0 ? (
              <p className="muted">No vulnerabilities linked.</p>
            ) : (
              <ul className="list">
                {incident.vulnerabilities.map((vulnerability) => (
                  <li key={vulnerability.id}>
                    <strong>{vulnerability.cve_id ?? 'No CVE'}</strong>
                    <span className="muted"> · {vulnerability.title}</span>
                    <span className="list__aside">
                      {vulnerability.cvss_score !== null && <span className="muted">CVSS {vulnerability.cvss_score.toFixed(1)}</span>}
                      <SeverityBadge value={vulnerability.severity} />
                      <span className="badge">{humanize(vulnerability.status)}</span>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <EditPanel key={incident.updated_at} incident={incident} onSaved={reload} />
        </div>

        <div className="stack">
          <TransitionPanel incident={incident} onDone={reload} />

          <section className="card">
            <h2>Audit trail</h2>
            <ol className="timeline">
              {[...history].reverse().map((entry) => (
                <li key={entry.id}>
                  <div>
                    {entry.from_status ? (
                      <>
                        <StatusBadge value={entry.from_status} /> → <StatusBadge value={entry.to_status} />
                      </>
                    ) : (
                      <>Created as <StatusBadge value={entry.to_status} /></>
                    )}
                  </div>
                  {entry.comment && <p className="timeline__comment">{entry.comment}</p>}
                  <span className="muted timeline__when">
                    {formatDateTime(entry.changed_at)}
                    {entry.changed_by && ` · ${entry.changed_by}`}
                  </span>
                </li>
              ))}
            </ol>
          </section>
        </div>
      </div>
    </>
  )
}

function TransitionPanel({ incident, onDone }: { incident: Incident; onDone: () => void }) {
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()

  async function move(target: IncidentStatus) {
    if (target === 'closed' && !window.confirm('Closing an incident is final. Continue?')) return
    setBusy(true)
    setError(undefined)
    try {
      await api.transitionIncident(incident.id, target, comment.trim())
      setComment('')
      onDone()
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card">
      <h2>Workflow</h2>
      {incident.allowed_transitions.length === 0 ? (
        <p className="muted">This incident is closed. It is a final record and cannot change any more.</p>
      ) : (
        <>
          <label className="field">
            <span>Comment (optional, saved in the audit trail)</span>
            <textarea rows={2} maxLength={2000} value={comment} onChange={(e) => setComment(e.target.value)} />
          </label>
          <div className="actions">
            {incident.allowed_transitions.map((target) => (
              <button
                key={target}
                className={target === 'closed' ? 'btn' : 'btn btn--primary'}
                disabled={busy}
                onClick={() => move(target)}
              >
                {transitionLabel(incident.status, target)}
              </button>
            ))}
          </div>
        </>
      )}
      {error && <ErrorMessage message={error} />}
    </section>
  )
}

function EditPanel({ incident, onSaved }: { incident: Incident; onSaved: () => void }) {
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(incident.title)
  const [description, setDescription] = useState(incident.description ?? '')
  const [severity, setSeverity] = useState<Severity>(incident.severity)
  const [category, setCategory] = useState<IncidentCategory>(incident.category)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()

  const locked = incident.status === 'closed'

  async function save(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(undefined)
    try {
      await api.updateIncident(incident.id, {
        title: title.trim(),
        description: description.trim(),
        severity,
        category,
      })
      setEditing(false)
      onSaved()
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card">
      <div className="card__header">
        <h2>Details</h2>
        {!editing && (
          <button className="btn btn--small" disabled={locked} onClick={() => setEditing(true)} title={locked ? 'Closed incidents are read-only' : undefined}>
            Edit
          </button>
        )}
      </div>
      {!editing ? (
        <p className="muted">
          {locked
            ? 'Closed incidents are read-only.'
            : 'Changing the severity recalculates the priority automatically.'}
        </p>
      ) : (
        <form onSubmit={save} className="form">
          <label className="field">
            <span>Title</span>
            <input type="text" required maxLength={300} value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label className="field">
            <span>Description</span>
            <textarea rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
          </label>
          <div className="row">
            <label className="field">
              <span>Severity</span>
              <select value={severity} onChange={(e) => setSeverity(e.target.value as Severity)}>
                {SEVERITIES.map((option) => (
                  <option key={option} value={option}>{humanize(option)}</option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Category</span>
              <select value={category} onChange={(e) => setCategory(e.target.value as IncidentCategory)}>
                {INCIDENT_CATEGORIES.map((option) => (
                  <option key={option} value={option}>{humanize(option)}</option>
                ))}
              </select>
            </label>
          </div>
          {error && <ErrorMessage message={error} />}
          <div className="actions">
            <button type="submit" className="btn btn--primary" disabled={busy}>Save changes</button>
            <button type="button" className="btn" disabled={busy} onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </form>
      )}
    </section>
  )
}
