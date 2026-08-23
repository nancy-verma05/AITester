export function EmptyState({ hasSearch }) {
  return (
    <div className="text-center text-xs text-slate-400 dark:text-slate-500 py-8 px-2">
      {hasSearch ? 'No jobs match your search.' : 'No jobs in this stage yet.'}
    </div>
  )
}
