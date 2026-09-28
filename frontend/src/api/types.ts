// Tipos que espelham os schemas do backend (backend/app/schemas). Os valores
// dos enums são listas `as const` (e não `enum` do TS) para poderem também
// alimentar dropdowns e filtros.

export const INCIDENT_STATUSES = ['open', 'investigating', 'mitigated', 'resolved', 'closed'] as const
export type IncidentStatus = (typeof INCIDENT_STATUSES)[number]

export const SEVERITIES = ['low', 'medium', 'high', 'critical'] as const
export type Severity = (typeof SEVERITIES)[number]

export const PRIORITIES = ['P1', 'P2', 'P3', 'P4'] as const
export type Priority = (typeof PRIORITIES)[number]

export const INCIDENT_CATEGORIES = [
  'malware',
  'phishing',
  'unauthorized_access',
  'data_breach',
  'denial_of_service',
  'misconfiguration',
  'other',
] as const
export type IncidentCategory = (typeof INCIDENT_CATEGORIES)[number]

export const CRITICALITIES = SEVERITIES
export type Criticality = Severity

export const ASSET_TYPES = [
  'server',
  'workstation',
  'network_device',
  'application',
  'database',
  'cloud_service',
  'other',
] as const
export type AssetType = (typeof ASSET_TYPES)[number]

export const VULNERABILITY_STATUSES = ['open', 'mitigated', 'patched', 'accepted'] as const
export type VulnerabilityStatus = (typeof VULNERABILITY_STATUSES)[number]

export interface Asset {
  id: number
  name: string
  asset_type: AssetType
  criticality: Criticality
  ip_address: string | null
  owner: string | null
  description: string | null
  created_at: string
  updated_at: string
}

export interface Vulnerability {
  id: number
  cve_id: string | null
  title: string
  description: string | null
  cvss_score: number | null
  severity: Severity
  status: VulnerabilityStatus
  asset_id: number | null
  created_at: string
  updated_at: string
}

export interface IncidentSummary {
  id: number
  title: string
  description: string | null
  category: IncidentCategory
  severity: Severity
  priority: Priority
  status: IncidentStatus
  resolved_at: string | null
  closed_at: string | null
  created_at: string
  updated_at: string
}

export interface Incident extends IncidentSummary {
  assets: Asset[]
  vulnerabilities: Vulnerability[]
  allowed_transitions: IncidentStatus[]
}

export interface StatusHistoryEntry {
  id: number
  incident_id: number
  from_status: IncidentStatus | null
  to_status: IncidentStatus
  changed_by: string | null
  comment: string | null
  changed_at: string
}

export interface IncidentCreate {
  title: string
  description?: string
  category: IncidentCategory
  severity: Severity
  asset_ids: number[]
  vulnerability_ids: number[]
}

export type IncidentUpdate = Partial<IncidentCreate>

export interface IncidentFilters {
  status?: IncidentStatus
  severity?: Severity
  priority?: Priority
  category?: IncidentCategory
  q?: string
  sort?: 'newest' | 'priority'
  skip?: number
  limit?: number
}

export interface DashboardSummary {
  incidents: {
    total: number
    active: number
    by_status: Record<IncidentStatus, number>
    active_by_severity: Record<Severity, number>
    active_by_priority: Record<Priority, number>
  }
  assets: { total: number; by_criticality: Record<Criticality, number> }
  vulnerabilities: {
    total: number
    by_status: Record<VulnerabilityStatus, number>
    by_severity: Record<Severity, number>
  }
}
