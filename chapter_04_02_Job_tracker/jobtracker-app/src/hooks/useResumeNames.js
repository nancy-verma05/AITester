import { useCallback, useEffect, useState } from 'react'
import { getAllResumeNames, upsertResumeName } from '../db/db'

export function useResumeNames() {
  const [resumeNames, setResumeNames] = useState([])

  useEffect(() => {
    let cancelled = false
    getAllResumeNames().then((names) => {
      if (!cancelled) setResumeNames(names)
    })
    return () => {
      cancelled = true
    }
  }, [])

  const registerResumeName = useCallback(async (name) => {
    if (!name || !name.trim()) return
    const trimmed = name.trim()
    await upsertResumeName(trimmed)
    setResumeNames((prev) => (prev.includes(trimmed) ? prev : [...prev, trimmed].sort()))
  }, [])

  const reload = useCallback(async () => {
    setResumeNames(await getAllResumeNames())
  }, [])

  return { resumeNames, registerResumeName, reload }
}
