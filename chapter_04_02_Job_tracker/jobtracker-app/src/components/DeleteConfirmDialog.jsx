export function DeleteConfirmDialog({ job, onCancel, onConfirm }) {
  if (!job) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-xl p-5">
        <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
          Delete this job application?
        </h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          {job.company} — {job.title}
        </p>
        <p className="mt-1 text-xs text-slate-400">This cannot be undone.</p>
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-1.5 text-sm rounded-md border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => onConfirm(job.id)}
            className="px-3 py-1.5 text-sm rounded-md bg-rose-600 text-white hover:bg-rose-700"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}
