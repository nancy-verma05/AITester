import { useState } from 'react'
import { useJobs } from './hooks/useJobs'
import { useResumeNames } from './hooks/useResumeNames'
import { useTheme } from './hooks/useTheme'
import { downloadExport, importAllData } from './db/backup'
import { Header } from './components/Header'
import { Board } from './components/Board'
import { JobFormModal } from './components/JobFormModal'
import { DeleteConfirmDialog } from './components/DeleteConfirmDialog'

export default function App() {
  const { jobs, createJob, editJob, removeJob, moveJobStatus, reorderWithinStatus, jobsByStatus, reload } =
    useJobs()
  const { resumeNames, registerResumeName, reload: reloadResumeNames } = useResumeNames()
  const { theme, toggleTheme } = useTheme()

  const [searchTerm, setSearchTerm] = useState('')
  const [formState, setFormState] = useState(null) // { mode: 'add' | 'edit', job? }
  const [jobPendingDelete, setJobPendingDelete] = useState(null)
  const [importError, setImportError] = useState('')

  function handleSaveJob(values) {
    if (formState?.mode === 'edit') {
      editJob(formState.job.id, values)
    } else {
      createJob(values)
    }
    setFormState(null)
  }

  async function handleImportFile(file) {
    setImportError('')
    try {
      const text = await file.text()
      const payload = JSON.parse(text)
      await importAllData(payload)
      await Promise.all([reload(), reloadResumeNames()])
    } catch (err) {
      setImportError(err.message || 'Failed to import file.')
    }
  }

  return (
    <div className="h-screen flex flex-col bg-slate-50 dark:bg-slate-950">
      <Header
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        theme={theme}
        onToggleTheme={toggleTheme}
        onAddJob={() => setFormState({ mode: 'add' })}
        onExport={downloadExport}
        onImportFile={handleImportFile}
      />

      {importError && (
        <div className="px-4 py-2 text-sm text-rose-700 bg-rose-50 dark:bg-rose-950 dark:text-rose-300 border-b border-rose-200 dark:border-rose-900">
          {importError}
        </div>
      )}

      <Board
        jobs={jobs}
        searchTerm={searchTerm}
        jobsByStatus={jobsByStatus}
        onMoveJobStatus={moveJobStatus}
        onReorderWithinStatus={reorderWithinStatus}
        onEditJob={(job) => setFormState({ mode: 'edit', job })}
        onDeleteJob={setJobPendingDelete}
      />

      {formState && (
        <JobFormModal
          mode={formState.mode}
          job={formState.job}
          resumeNames={resumeNames}
          onClose={() => setFormState(null)}
          onSave={handleSaveJob}
          onRegisterResumeName={registerResumeName}
        />
      )}

      <DeleteConfirmDialog
        job={jobPendingDelete}
        onCancel={() => setJobPendingDelete(null)}
        onConfirm={(id) => {
          removeJob(id)
          setJobPendingDelete(null)
        }}
      />
    </div>
  )
}
