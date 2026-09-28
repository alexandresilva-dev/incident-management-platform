import type { IncidentStatus, Priority, Severity } from '../api/types.ts'
import { humanize } from '../lib/format.ts'

export function SeverityBadge({ value }: { value: Severity }) {
  return <span className={`badge badge--${value}`}>{humanize(value)}</span>
}

export function PriorityBadge({ value }: { value: Priority }) {
  return <span className={`badge badge--priority-${value.toLowerCase()}`}>{value}</span>
}

export function StatusBadge({ value }: { value: IncidentStatus }) {
  return <span className={`badge badge--status-${value}`}>{humanize(value)}</span>
}
