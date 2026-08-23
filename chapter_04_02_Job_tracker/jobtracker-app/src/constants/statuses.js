/** @type {{id: import('../types').JobStatus, label: string, accent: string, dot: string}[]} */
export const STATUSES = [
  {
    id: 'wishlist',
    label: 'Wishlist',
    accent: 'border-l-slate-400',
    dot: 'bg-slate-400',
  },
  {
    id: 'applied',
    label: 'Applied',
    accent: 'border-l-blue-500',
    dot: 'bg-blue-500',
  },
  {
    id: 'followup',
    label: 'Follow-up',
    accent: 'border-l-amber-500',
    dot: 'bg-amber-500',
  },
  {
    id: 'interview',
    label: 'Interview',
    accent: 'border-l-purple-500',
    dot: 'bg-purple-500',
  },
  {
    id: 'offer',
    label: 'Offer',
    accent: 'border-l-emerald-500',
    dot: 'bg-emerald-500',
  },
  {
    id: 'rejected',
    label: 'Rejected',
    accent: 'border-l-rose-500',
    dot: 'bg-rose-500',
  },
]

export const STATUS_IDS = STATUSES.map((s) => s.id)

export const DEFAULT_STATUS = 'wishlist'

export function getStatus(id) {
  return STATUSES.find((s) => s.id === id) ?? STATUSES[0]
}
