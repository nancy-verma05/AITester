import { useRef } from 'react'
import { Download, Plus, Upload } from 'lucide-react'
import { SearchBar } from './SearchBar'
import { ThemeToggle } from './ThemeToggle'

export function Header({ searchTerm, onSearchChange, theme, onToggleTheme, onAddJob, onExport, onImportFile }) {
  const fileInputRef = useRef(null)

  function handleImportClick() {
    fileInputRef.current?.click()
  }

  function handleFileChange(e) {
    const file = e.target.files?.[0]
    if (file) onImportFile(file)
    e.target.value = ''
  }

  return (
    <header className="flex flex-wrap items-center gap-3 px-4 py-3 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950">
      <h1 className="text-lg font-bold text-slate-900 dark:text-slate-100 mr-2 shrink-0">
        Job Tracker
      </h1>

      <SearchBar value={searchTerm} onChange={onSearchChange} />

      <div className="flex items-center gap-2 ml-auto">
        <button
          type="button"
          onClick={onExport}
          title="Export data as JSON"
          className="p-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
        >
          <Download className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={handleImportClick}
          title="Import data from JSON"
          className="p-2 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
        >
          <Upload className="h-4 w-4" />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/json"
          onChange={handleFileChange}
          className="hidden"
        />
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        <button
          type="button"
          onClick={onAddJob}
          className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          Add Job
        </button>
      </div>
    </header>
  )
}
