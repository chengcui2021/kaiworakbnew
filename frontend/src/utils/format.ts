export function formatNumber(value: number | string | undefined): string {
  return new Intl.NumberFormat('en-GB').format(Number(value || 0))
}

export function formatDate(value: string | Date | undefined): string {
  if (!value) return ''
  return new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' }).format(new Date(value))
}

export function formatDateTime(value: string | Date | undefined): string {
  if (!value) return ''
  return new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value)
  )
}

/** Cosine similarity (0-1) as a percentage, e.g. "87.3%". */
export function formatSimilarity(similarity: number | null | undefined): string {
  if (similarity == null || Number.isNaN(similarity)) return '—'
  return `${(similarity * 100).toFixed(1)}%`
}

/** Human-friendly relative time, e.g. "2 hours ago", "just now". */
export function formatRelativeTime(value: string | Date | undefined): string {
  if (!value) return ''
  const then = new Date(value).getTime()
  const diffSec = Math.round((Date.now() - then) / 1000)
  if (Number.isNaN(diffSec)) return ''
  if (diffSec < 45) return 'just now'
  const units: Array<[number, string]> = [
    [60, 'second'],
    [60, 'minute'],
    [24, 'hour'],
    [7, 'day'],
    [4.345, 'week'],
    [12, 'month'],
    [Number.POSITIVE_INFINITY, 'year'],
  ]
  let amount = diffSec
  let unit = 'second'
  for (const [size, name] of units) {
    if (amount < size) {
      unit = name
      break
    }
    amount = amount / size
    unit = name
  }
  const rounded = Math.max(1, Math.floor(amount))
  return `${rounded} ${unit}${rounded === 1 ? '' : 's'} ago`
}
