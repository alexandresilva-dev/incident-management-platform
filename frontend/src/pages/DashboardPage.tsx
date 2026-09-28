import { useCallback } from 'react'
import { Link } from 'react-router'
import { api } from '../api/client.ts'
import {
  CRITICALITIES,
  INCIDENT_STATUSES,
  PRIORITIES,
  SEVERITIES,
  VULNERABILITY_STATUSES,
} from '../api/types.ts'
import { BarList } from '../components/BarList.tsx'
import { PriorityBadge, SeverityBadge, StatusBadge } from '../components/Badges.tsx'
import { ErrorMessage, Loading } from '../components/StateViews.tsx'
import { useApi } from '../hooks/useApi.ts'
import { humanize } from '../lib/format.ts'

const ATTENTION_LIMIT = 5

export default function DashboardPage() {
  const load = useCallback(
    () =>
      Promise.all([
        api.getDashboardSummary(),
        // A API ordena por prioridade; os fechados filtram-se aqui.
        api.listIncidents({ sort: 'priority', limit: 50 }),
      ]),
    [],
  )
  const { data, error, reload } = useApi(load)

  if (error) return <ErrorMessage message={error} onRetry={reload} />
  if (!data) return <Loading />

  const [summary, incidents] = data
  const { incidents: inc, assets, vulnerabilities: vulns } = summary
  const needsAttention = incidents
    .filter((incident) => incident.status !== 'closed')
    .slice(0, ATTENTION_LIMIT)

  return (
    <>
      <div className="page-header">
        <h1>Dashboard</h1>
        <Link to="/incidents/new" className="btn btn--primary">New incident</Link>
      </div>

      <div className="stats">
        <Stat label="Active incidents" value={inc.active} hint={`${inc.total} in total`} to="/incidents" />
        <Stat label="P1 incidents" value={inc.active_by_priority.P1} hint="active, most urgent" tone="critical" to="/incidents?priority=P1" />
        <Stat label="Waiting for triage" value={inc.by_status.open} hint="status: open" to="/incidents?status=open" />
        <Stat label="Open vulnerabilities" value={vulns.by_status.open} hint={`${vulns.total} tracked`} />
        <Stat label="Assets" value={assets.total} hint={`${assets.by_criticality.critical} critical`} />
      </div>

      <section className="card">
        <div className="card__header">
          <h2>Needs attention</h2>
          <Link to="/incidents">View all</Link>
        </div>
        {needsAttention.length === 0 ? (
          <p className="muted">No active incidents. Nothing needs attention.</p>
        ) : (
          <ul className="list">
            {needsAttention.map((incident) => (
              <li key={incident.id}>
                <PriorityBadge value={incident.priority} />
                <Link to={`/incidents/${incident.id}`}>{incident.title}</Link>
                <span className="list__aside">
                  <SeverityBadge value={incident.severity} />
                  <StatusBadge value={incident.status} />
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="grid-3">
        <section className="card">
          <h2>Incidents by status</h2>
          <BarList
            bars={INCIDENT_STATUSES.map((status) => ({
              label: humanize(status),
              value: inc.by_status[status],
              tone: status === 'open' ? 'critical' : status === 'investigating' ? 'violet' : status === 'mitigated' ? 'medium' : status === 'resolved' ? 'ok' : 'neutral',
            }))}
          />
        </section>

        <section className="card">
          <h2>Active by priority</h2>
          <BarList
            bars={PRIORITIES.map((priority, index) => ({
              label: priority,
              value: inc.active_by_priority[priority],
              tone: ['critical', 'high', 'medium', 'low'][index],
            }))}
          />
        </section>

        <section className="card">
          <h2>Active by severity</h2>
          <BarList
            bars={[...SEVERITIES].reverse().map((severity) => ({
              label: humanize(severity),
              value: inc.active_by_severity[severity],
              tone: severity,
            }))}
          />
        </section>

        <section className="card">
          <h2>Vulnerabilities by status</h2>
          <BarList
            bars={VULNERABILITY_STATUSES.map((status) => ({
              label: humanize(status),
              value: vulns.by_status[status],
              tone: status === 'open' ? 'critical' : status === 'mitigated' ? 'medium' : status === 'patched' ? 'ok' : 'neutral',
            }))}
          />
        </section>

        <section className="card">
          <h2>Vulnerabilities by severity</h2>
          <BarList
            bars={[...SEVERITIES].reverse().map((severity) => ({
              label: humanize(severity),
              value: vulns.by_severity[severity],
              tone: severity,
            }))}
          />
        </section>

        <section className="card">
          <h2>Assets by criticality</h2>
          <BarList
            bars={[...CRITICALITIES].reverse().map((criticality) => ({
              label: humanize(criticality),
              value: assets.by_criticality[criticality],
              tone: criticality,
            }))}
          />
        </section>
      </div>
    </>
  )
}

function Stat({
  label,
  value,
  hint,
  tone,
  to,
}: {
  label: string
  value: number
  hint?: string
  tone?: string
  to?: string
}) {
  const content = (
    <>
      <span className="stat__label">{label}</span>
      <span className={`stat__value${tone ? ` stat__value--${tone}` : ''}`}>{value}</span>
      {hint && <span className="stat__hint muted">{hint}</span>}
    </>
  )
  return to ? (
    <Link to={to} className="stat stat--link">{content}</Link>
  ) : (
    <div className="stat">{content}</div>
  )
}
