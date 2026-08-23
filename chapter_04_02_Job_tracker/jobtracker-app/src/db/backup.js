import { getAllJobs, getAllResumeNames, clearAll, putAll } from './db'

const EXPORT_VERSION = 1

export async function exportAllData() {
  const [jobs, resumes] = await Promise.all([getAllJobs(), getAllResumeNames()])
  return {
    version: EXPORT_VERSION,
    exportedAt: new Date().toISOString(),
    jobs,
    resumes,
  }
}

export async function downloadExport() {
  const payload = await exportAllData()
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const date = new Date().toISOString().slice(0, 10)
  a.href = url
  a.download = `job-tracker-backup-${date}.json`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function isValidJob(job) {
  return (
    job &&
    typeof job.id === 'string' &&
    typeof job.company === 'string' &&
    typeof job.title === 'string' &&
    typeof job.status === 'string'
  )
}

/**
 * @param {import('../types').ExportPayload} payload
 */
export async function importAllData(payload) {
  if (!payload || typeof payload !== 'object') {
    throw new Error('Import file is not valid JSON data.')
  }
  if (!Array.isArray(payload.jobs) || !payload.jobs.every(isValidJob)) {
    throw new Error('Import file is missing a valid "jobs" list.')
  }
  const resumes = Array.isArray(payload.resumes)
    ? payload.resumes.filter((r) => typeof r === 'string')
    : []

  await clearAll()
  await putAll(payload.jobs, resumes)
}
