import { describe, expect, it } from 'vitest'
import { transitionLabel } from './workflow.ts'

describe('transitionLabel', () => {
  it('distinguishes the different ways of going back to investigating', () => {
    expect(transitionLabel('open', 'investigating')).toBe('Start investigation')
    expect(transitionLabel('mitigated', 'investigating')).toBe('Mitigation failed')
    expect(transitionLabel('resolved', 'investigating')).toBe('Reopen')
  })

  it('labels the forward steps', () => {
    expect(transitionLabel('investigating', 'mitigated')).toBe('Mark mitigated')
    expect(transitionLabel('mitigated', 'resolved')).toBe('Mark resolved')
    expect(transitionLabel('resolved', 'closed')).toBe('Close incident')
  })
})
