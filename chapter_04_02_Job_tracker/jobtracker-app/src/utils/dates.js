export function todayISO() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function startOfDay(date) {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  return d
}

/**
 * @param {string} isoDateString
 * @returns {number|null} days elapsed since the given date, clamped to a minimum of 0
 */
export function daysSince(isoDateString) {
  if (!isoDateString) return null
  const then = startOfDay(isoDateString)
  if (Number.isNaN(then.getTime())) return null
  const now = startOfDay(new Date())
  const diff = Math.floor((now.getTime() - then.getTime()) / 86_400_000)
  return Math.max(0, diff)
}

export function formatDate(isoDateString) {
  if (!isoDateString) return '—'
  const d = new Date(isoDateString)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}
