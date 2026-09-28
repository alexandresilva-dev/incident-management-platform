import { useCallback, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { api } from '../api/client.ts'
import {
  INCIDENT_CATEGORIES,
  SEVERITIES,
  type IncidentCategory,
  type Severity,
} from '../api/types.ts'
import { ErrorMessage, Loading } from '../components/StateViews.tsx'
import { useApi } from '../hooks/useApi.ts'
import { humanize } from '../lib/format.ts'

export default function NewIncidentPage() {
  const navigate = useNavigate()

  const loadOptions = useCallback(
    () => Promise.all([api.listAssets(), api.listVulnerabilities()]),
    [],
  )
  const { data, error: loadError, reload } = useApi(loadOptions)

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState<IncidentCategory>('other')
  const [severity, setSeverity] = useState<Severity>('medium')
  const [assetIds, setAssetIds] = useState<number[]>([])
  const [vulnerabilityIds, setVulnerabilityIds] = useState<number[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(undefined)
    try {
      const created = await api.createIncident({
        title: title.trim(),
        description: description.trim() || undefined,
        category,
        severity,
        asset_ids: assetIds,
        vulnerability_ids: vulnerabilityIds,
      })
      navigate(`/incidents/${created.id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setBusy(false)
    }
  }

  if (loadError) return <ErrorMessage message={loadError} onRetry={reload} />
  if (!data) return <Loading />
  const [assets, vulnerabilities] = data

  return (
    <>
      <p>
        <Link to="/incidents">← All incidents</Link>
      </p>
      <div className="page-header">
        <h1>New incident</h1>
      </div>

      <form className="card form" onSubmit={submit}>
        <label className="field">
          <span>Title</span>
          <input
            type="text"
            required
            maxLength={300}
            placeholder="e.g. Suspicious logins on the VPN gateway"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
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

        <fieldset className="checklist">
          <legend>Affected assets</legend>
          {assets.length === 0 && <p className="muted">No assets registered yet.</p>}
          {assets.map((asset) => (
            <label key={asset.id}>
              <input
                type="checkbox"
                checked={assetIds.includes(asset.id)}
                onChange={() => setAssetIds(toggle(assetIds, asset.id))}
              />
              {asset.name}
              <span className="muted"> · {humanize(asset.asset_type)} · {asset.criticality} criticality</span>
            </label>
          ))}
        </fieldset>

        <fieldset className="checklist">
          <legend>Related vulnerabilities</legend>
          {vulnerabilities.length === 0 && <p className="muted">No vulnerabilities registered yet.</p>}
          {vulnerabilities.map((vulnerability) => (
            <label key={vulnerability.id}>
              <input
                type="checkbox"
                checked={vulnerabilityIds.includes(vulnerability.id)}
                onChange={() => setVulnerabilityIds(toggle(vulnerabilityIds, vulnerability.id))}
              />
              {vulnerability.cve_id ?? 'No CVE'}
              <span className="muted"> · {vulnerability.title}</span>
            </label>
          ))}
        </fieldset>

        <p className="muted">The priority is calculated automatically from the severity and the criticality of the affected assets.</p>

        {error && <ErrorMessage message={error} />}
        <div className="actions">
          <button type="submit" className="btn btn--primary" disabled={busy || !title.trim()}>
            {busy ? 'Creating…' : 'Create incident'}
          </button>
          <Link to="/incidents" className="btn">Cancel</Link>
        </div>
      </form>
    </>
  )
}

function toggle(list: number[], id: number): number[] {
  return list.includes(id) ? list.filter((item) => item !== id) : [...list, id]
}
