import type { IncidentStatus } from '../api/types.ts'
import { humanize } from './format.ts'

/** Texto do botão de uma transição. As regras em si vêm do backend (`allowed_transitions`). */
export function transitionLabel(from: IncidentStatus, to: IncidentStatus): string {
  switch (to) {
    case 'investigating':
      if (from === 'open') return 'Start investigation'
      if (from === 'mitigated') return 'Mitigation failed'
      return 'Reopen'
    case 'mitigated':
      return 'Mark mitigated'
    case 'resolved':
      return 'Mark resolved'
    case 'closed':
      return 'Close incident'
    default:
      return humanize(to)
  }
}
