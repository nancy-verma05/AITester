import { useMemo, useState } from 'react'
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import { arrayMove } from '@dnd-kit/sortable'
import { STATUSES } from '../constants/statuses'
import { Column } from './Column'
import { JobCard } from './JobCard'

export function Board({ jobs, searchTerm, jobsByStatus, onMoveJobStatus, onReorderWithinStatus, onEditJob, onDeleteJob }) {
  const [activeJob, setActiveJob] = useState(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  )

  const columns = useMemo(
    () =>
      STATUSES.map((status) => ({
        status,
        jobs: jobsByStatus(status.id, searchTerm),
      })),
    [jobsByStatus, searchTerm]
  )

  function findJob(id) {
    return jobs.find((j) => j.id === id)
  }

  function resolveTargetStatus(over) {
    if (!over) return null
    const overStatus = STATUSES.find((s) => s.id === over.id)
    if (overStatus) return overStatus.id
    const overJob = findJob(over.id)
    return overJob ? overJob.status : null
  }

  function handleDragStart(event) {
    setActiveJob(findJob(event.active.id) ?? null)
  }

  function handleDragEnd(event) {
    const { active, over } = event
    setActiveJob(null)
    if (!over) return

    const activeJobRecord = findJob(active.id)
    if (!activeJobRecord) return

    const targetStatus = resolveTargetStatus(over)
    if (!targetStatus) return

    if (targetStatus !== activeJobRecord.status) {
      onMoveJobStatus(active.id, targetStatus)
      return
    }

    const overJob = findJob(over.id)
    if (!overJob || overJob.id === active.id) return

    const columnJobs = jobsByStatus(targetStatus, searchTerm)
    const oldIndex = columnJobs.findIndex((j) => j.id === active.id)
    const newIndex = columnJobs.findIndex((j) => j.id === over.id)
    if (oldIndex === -1 || newIndex === -1) return

    const reordered = arrayMove(columnJobs, oldIndex, newIndex)
    onReorderWithinStatus(targetStatus, reordered.map((j) => j.id))
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex-1 overflow-x-auto">
        <div className="flex gap-3 h-full p-4 min-h-0">
          {columns.map(({ status, jobs: colJobs }) => (
            <Column
              key={status.id}
              status={status}
              jobs={colJobs}
              hasSearch={Boolean(searchTerm.trim())}
              onEditJob={onEditJob}
              onDeleteJob={onDeleteJob}
            />
          ))}
        </div>
      </div>
      <DragOverlay>
        {activeJob ? <JobCard job={activeJob} isOverlay onEdit={() => {}} onDelete={() => {}} /> : null}
      </DragOverlay>
    </DndContext>
  )
}
