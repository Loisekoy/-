export function parseApiDate(value: string): Date {
  const includesTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
  return new Date(includesTimezone ? value : `${value}Z`)
}
