import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { ExternalLink, Pencil, Trash2 } from 'lucide-react'
import { daysSince } from '../utils/dates'
import { getStatus } from '../constants/statuses'

export function JobCard({ job, onEdit, onDelete, isOverlay = false }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: job.id,
    data: { status: job.status },
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  const status = getStatus(job.status)
  const days = daysSince(job.dateApplied)
  const daysLabel =
    days === null
      ? '—'
      : job.status === 'wishlist'
        ? days === 0
          ? 'Saved today'
          : `Saved ${days}d ago`
        : days === 0
          ? 'Applied today'
          : `${days}d since applied`

  return (
    <div
      ref={isOverlay ? undefined : setNodeRef}
      style={isOverlay ? undefined : style}
      {...(isOverlay ? {} : attributes)}
      {...(isOverlay ? {} : listeners)}
      onClick={() => !isOverlay && onEdit(job)}
      className={`group rounded-md border border-slate-200 dark:border-slate-700 border-l-4 ${status.accent} bg-white dark:bg-slate-900 shadow-sm hover:shadow-md transition-shadow p-3 cursor-pointer ${
        isDragging ? 'opacity-40' : ''
      } ${isOverlay ? 'shadow-lg rotate-1 cursor-grabbing' : ''}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-semibold text-sm text-slate-900 dark:text-slate-100 truncate">
            {job.company}
          </p>
          <p className="text-sm text-slate-600 dark:text-slate-400 truncate">{job.title}</p>
        </div>
        {job.linkedinUrl && (
          <a
            href={job.linkedinUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            title="Open LinkedIn job posting"
            className="shrink-0 text-slate-400 hover:text-blue-600 dark:hover:text-blue-400"
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        )}
      </div>

      <div className="mt-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          {job.resume && (
            <span className="inline-block max-w-full truncate rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-[11px] px-2 py-0.5">
              {job.resume}
            </span>
          )}
        </div>
        <span className="shrink-0 text-[11px] text-slate-400">{daysLabel}</span>
      </div>

      {!isOverlay && (
        <div className="mt-2 flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onEdit(job)
            }}
            title="Edit"
            className="p-1 rounded text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onDelete(job)
            }}
            title="Delete"
            className="p-1 rounded text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  )
}
