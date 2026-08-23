import { useMemo, useState } from 'react'
import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { JobCard } from './JobCard'
import { EmptyState } from './EmptyState'

export function Column({ status, jobs, hasSearch, onEditJob, onDeleteJob }) {
  const [sortOrder, setSortOrder] = useState('manual')
  const { setNodeRef, isOver } = useDroppable({ id: status.id })

  const sortedJobs = useMemo(() => {
    if (sortOrder === 'manual') return jobs
    const sorted = [...jobs].sort((a, b) => {
      const diff = new Date(a.dateApplied).getTime() - new Date(b.dateApplied).getTime()
      return sortOrder === 'newest' ? -diff : diff
    })
    return sorted
  }, [jobs, sortOrder])

  return (
    <div className="flex flex-col h-full min-w-[260px] w-[260px] shrink-0 rounded-lg bg-slate-100 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
      <div className="px-3 py-2 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 truncate">
            {status.label}
          </h2>
          <span className="shrink-0 text-xs font-medium rounded-full bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300 px-1.5 py-0.5">
            {jobs.length}
          </span>
        </div>
        <select
          value={sortOrder}
          onChange={(e) => setSortOrder(e.target.value)}
          title="Sort within column"
          className="text-[11px] bg-transparent border border-slate-300 dark:border-slate-700 rounded px-1 py-0.5 text-slate-500 dark:text-slate-400 focus:outline-none"
        >
          <option value="manual">Manual</option>
          <option value="newest">Newest</option>
          <option value="oldest">Oldest</option>
        </select>
      </div>

      <div
        ref={setNodeRef}
        className={`flex-1 overflow-y-auto px-2 py-2 space-y-2 min-h-[80px] ${
          isOver ? 'bg-blue-50 dark:bg-blue-950/30' : ''
        }`}
      >
        <SortableContext items={sortedJobs.map((j) => j.id)} strategy={verticalListSortingStrategy}>
          {sortedJobs.length === 0 ? (
            <EmptyState hasSearch={hasSearch} />
          ) : (
            sortedJobs.map((job) => (
              <JobCard key={job.id} job={job} onEdit={onEditJob} onDelete={onDeleteJob} />
            ))
          )}
        </SortableContext>
      </div>
    </div>
  )
}
