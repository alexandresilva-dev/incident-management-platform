import { describe, expect, it } from 'vitest'
import { humanize } from './format.ts'

describe('humanize', () => {
  it('turns snake_case values into readable labels', () => {
    expect(humanize('unauthorized_access')).toBe('Unauthorized access')
    expect(humanize('open')).toBe('Open')
    expect(humanize('P1')).toBe('P1')
  })
})
