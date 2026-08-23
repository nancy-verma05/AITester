import { useCallback, useEffect, useMemo, useState } from 'react'
import { getAllJobs, addJob, updateJob, updateJobs, deleteJob } from '../db/db'
import { newId } from '../utils/id'
import { todayISO } from '../utils/dates'
import { DEFAULT_STATUS } from '../constants/statuses'

export function useJobs() {
  const [jobs, setJobs] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    getAllJobs().then((loaded) => {
      if (!cancelled) {
        setJobs(loaded)
        setIsLoading(false)
      }
    })
    return () => {
      cancelled = true
    }
  }, [])

  const reload = useCallback(async () => {
    const loaded = await getAllJobs()
    setJobs(loaded)
  }, [])

  const createJob = useCallback(async (formValues) => {
    const now = new Date().toISOString()
    const job = {
      id: newId(),
      company: formValues.company.trim(),
      title: formValues.title.trim(),
      linkedinUrl: formValues.linkedinUrl?.trim() ?? '',
      resume: formValues.resume?.trim() ?? '',
      dateApplied: formValues.dateApplied || todayISO(),
      salaryRange: formValues.salaryRange?.trim() ?? '',
      notes: formValues.notes?.trim() ?? '',
      status: formValues.status || DEFAULT_STATUS,
      order: Date.now(),
      createdAt: now,
      updatedAt: now,
    }
    await addJob(job)
    setJobs((prev) => [job, ...prev])
    return job
  }, [])

  const editJob = useCallback(async (id, formValues) => {
    setJobs((prev) => {
      const existing = prev.find((j) => j.id === id)
      if (!existing) return prev
      const updated = {
        ...existing,
        company: formValues.company.trim(),
        title: formValues.title.trim(),
        linkedinUrl: formValues.linkedinUrl?.trim() ?? '',
        resume: formValues.resume?.trim() ?? '',
        dateApplied: formValues.dateApplied || existing.dateApplied,
        salaryRange: formValues.salaryRange?.trim() ?? '',
        notes: formValues.notes?.trim() ?? '',
        status: formValues.status || existing.status,
        updatedAt: new Date().toISOString(),
      }
      updateJob(updated)
      return prev.map((j) => (j.id === id ? updated : j))
    })
  }, [])

  const removeJob = useCallback(async (id) => {
    await deleteJob(id)
    setJobs((prev) => prev.filter((j) => j.id !== id))
  }, [])

  const moveJobStatus = useCallback(async (id, newStatus) => {
    setJobs((prev) => {
      const existing = prev.find((j) => j.id === id)
      if (!existing || existing.status === newStatus) return prev
      const maxOrder = prev
        .filter((j) => j.status === newStatus)
        .reduce((max, j) => Math.max(max, j.order ?? 0), 0)
      const updated = {
        ...existing,
        status: newStatus,
        order: maxOrder + 1,
        updatedAt: new Date().toISOString(),
      }
      updateJob(updated)
      return prev.map((j) => (j.id === id ? updated : j))
    })
  }, [])

  const reorderWithinStatus = useCallback(async (status, orderedIds) => {
    setJobs((prev) => {
      const byId = new Map(prev.map((j) => [j.id, j]))
      const changed = []
      orderedIds.forEach((id, index) => {
        const job = byId.get(id)
        if (job) {
          const updated = { ...job, order: index, updatedAt: new Date().toISOString() }
          byId.set(id, updated)
          changed.push(updated)
        }
      })
      if (changed.length) updateJobs(changed)
      return prev.map((j) => byId.get(j.id) ?? j)
    })
  }, [])

  const jobsByStatus = useCallback(
    (statusId, searchTerm) => {
      const term = (searchTerm ?? '').trim().toLowerCase()
      return jobs
        .filter((j) => j.status === statusId)
        .filter(
          (j) =>
            !term ||
            j.company.toLowerCase().includes(term) ||
            j.title.toLowerCase().includes(term)
        )
        .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
    },
    [jobs]
  )

  return useMemo(
    () => ({
      jobs,
      isLoading,
      reload,
      createJob,
      editJob,
      removeJob,
      moveJobStatus,
      reorderWithinStatus,
      jobsByStatus,
    }),
    [jobs, isLoading, reload, createJob, editJob, removeJob, moveJobStatus, reorderWithinStatus, jobsByStatus]
  )
}
