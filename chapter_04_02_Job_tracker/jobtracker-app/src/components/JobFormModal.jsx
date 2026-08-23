import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { STATUSES, DEFAULT_STATUS } from '../constants/statuses'
import { validateJobForm } from '../utils/validation'
import { todayISO } from '../utils/dates'

const EMPTY_FORM = {
  company: '',
  title: '',
  linkedinUrl: '',
  resume: '',
  dateApplied: todayISO(),
  salaryRange: '',
  notes: '',
  status: DEFAULT_STATUS,
}

export function JobFormModal({ mode, job, resumeNames, onClose, onSave, onRegisterResumeName }) {
  const [values, setValues] = useState(job ? { ...job } : EMPTY_FORM)
  const [hasSubmitted, setHasSubmitted] = useState(false)

  useEffect(() => {
    setValues(job ? { ...job } : EMPTY_FORM)
    setHasSubmitted(false)
  }, [job])

  const { errors, isValid } = validateJobForm(values)

  function update(field, value) {
    setValues((prev) => ({ ...prev, [field]: value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    setHasSubmitted(true)
    if (!isValid) return
    onSave(values)
  }

  const showErrors = hasSubmitted

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md max-h-[90vh] overflow-y-auto rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-slate-800">
          <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
            {mode === 'edit' ? 'Edit Job' : 'Add Job'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-5 py-4 space-y-4">
          <Field label="Company" required error={showErrors && errors.company}>
            <input
              type="text"
              value={values.company}
              onChange={(e) => update('company', e.target.value)}
              className={inputClass(showErrors && errors.company)}
              autoFocus
            />
          </Field>

          <Field label="Job title / role" required error={showErrors && errors.title}>
            <input
              type="text"
              value={values.title}
              onChange={(e) => update('title', e.target.value)}
              className={inputClass(showErrors && errors.title)}
            />
          </Field>

          <Field label="LinkedIn job URL" error={showErrors && errors.linkedinUrl}>
            <input
              type="url"
              value={values.linkedinUrl}
              onChange={(e) => update('linkedinUrl', e.target.value)}
              placeholder="https://www.linkedin.com/jobs/..."
              className={inputClass(showErrors && errors.linkedinUrl)}
            />
          </Field>

          <Field label="Resume used">
            <input
              type="text"
              list="resume-names"
              value={values.resume}
              onChange={(e) => update('resume', e.target.value)}
              onBlur={(e) => onRegisterResumeName(e.target.value)}
              placeholder="SDE_Resume_v3"
              className={inputClass()}
            />
            <datalist id="resume-names">
              {resumeNames.map((name) => (
                <option key={name} value={name} />
              ))}
            </datalist>
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Date applied">
              <input
                type="date"
                value={values.dateApplied}
                onChange={(e) => update('dateApplied', e.target.value)}
                className={inputClass()}
              />
            </Field>
            <Field label="Status">
              <select
                value={values.status}
                onChange={(e) => update('status', e.target.value)}
                className={inputClass()}
              >
                {STATUSES.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <Field label="Salary range">
            <input
              type="text"
              value={values.salaryRange}
              onChange={(e) => update('salaryRange', e.target.value)}
              placeholder="₹25-30 LPA or $150-180K"
              className={inputClass()}
            />
          </Field>

          <Field label="Notes">
            <textarea
              value={values.notes}
              onChange={(e) => update('notes', e.target.value)}
              rows={3}
              placeholder="Recruiter name, referral info..."
              className={inputClass()}
            />
          </Field>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-sm rounded-md border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-3 py-1.5 text-sm rounded-md bg-blue-600 text-white hover:bg-blue-700"
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function Field({ label, required, error, children }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
        {label}
        {required && <span className="text-rose-500"> *</span>}
      </span>
      {children}
      {error && <span className="block text-xs text-rose-500 mt-1">{error}</span>}
    </label>
  )
}

function inputClass(hasError) {
  return `w-full text-sm rounded-md border bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
    hasError ? 'border-rose-500' : 'border-slate-300 dark:border-slate-700'
  }`
}
