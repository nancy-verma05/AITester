import { openDB } from 'idb'

const DB_NAME = 'jobtracker-db'
const DB_VERSION = 1
const JOBS_STORE = 'jobs'
const RESUMES_STORE = 'resumes'

let dbPromise = null

export function getDb() {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        const jobs = db.createObjectStore(JOBS_STORE, { keyPath: 'id' })
        jobs.createIndex('status', 'status')
        jobs.createIndex('company', 'company')

        db.createObjectStore(RESUMES_STORE, { keyPath: 'name' })
      },
    })
  }
  return dbPromise
}

export async function getAllJobs() {
  const db = await getDb()
  return db.getAll(JOBS_STORE)
}

export async function addJob(job) {
  const db = await getDb()
  await db.add(JOBS_STORE, job)
  await upsertResumeName(job.resume)
  return job
}

export async function updateJob(job) {
  const db = await getDb()
  await db.put(JOBS_STORE, job)
  await upsertResumeName(job.resume)
  return job
}

export async function updateJobs(jobs) {
  const db = await getDb()
  const tx = db.transaction(JOBS_STORE, 'readwrite')
  await Promise.all(jobs.map((job) => tx.store.put(job)))
  await tx.done
  return jobs
}

export async function deleteJob(id) {
  const db = await getDb()
  await db.delete(JOBS_STORE, id)
}

export async function getAllResumeNames() {
  const db = await getDb()
  const keys = await db.getAllKeys(RESUMES_STORE)
  return keys.sort((a, b) => a.localeCompare(b))
}

export async function upsertResumeName(name) {
  if (!name || !name.trim()) return
  const db = await getDb()
  await db.put(RESUMES_STORE, { name: name.trim(), createdAt: new Date().toISOString() })
}

export async function clearAll() {
  const db = await getDb()
  const tx = db.transaction([JOBS_STORE, RESUMES_STORE], 'readwrite')
  await Promise.all([tx.objectStore(JOBS_STORE).clear(), tx.objectStore(RESUMES_STORE).clear()])
  await tx.done
}

export async function putAll(jobs, resumeNames) {
  const db = await getDb()
  const tx = db.transaction([JOBS_STORE, RESUMES_STORE], 'readwrite')
  await Promise.all([
    ...jobs.map((job) => tx.objectStore(JOBS_STORE).put(job)),
    ...resumeNames.map((name) =>
      tx.objectStore(RESUMES_STORE).put({ name, createdAt: new Date().toISOString() })
    ),
  ])
  await tx.done
}

export const STORE_NAMES = { JOBS_STORE, RESUMES_STORE }
