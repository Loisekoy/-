import { describe, expect, it } from 'vitest'
import { parseApiDate } from './datetime'

describe('parseApiDate', () => {
  it('treats a timezone-less API timestamp as UTC', () => {
    expect(parseApiDate('2026-09-16T02:00:00').toISOString()).toBe(
      '2026-09-16T02:00:00.000Z',
    )
  })

  it('preserves timestamps that already include an offset', () => {
    expect(parseApiDate('2026-09-16T10:00:00+08:00').toISOString()).toBe(
      '2026-09-16T02:00:00.000Z',
    )
  })
})
