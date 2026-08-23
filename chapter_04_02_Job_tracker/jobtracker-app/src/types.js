/**
 * @typedef {'wishlist'|'applied'|'followup'|'interview'|'offer'|'rejected'} JobStatus
 */

/**
 * @typedef {Object} Job
 * @property {string} id
 * @property {string} company
 * @property {string} title
 * @property {string} linkedinUrl
 * @property {string} resume
 * @property {string} dateApplied - ISO date string (yyyy-mm-dd)
 * @property {string} salaryRange
 * @property {string} notes
 * @property {JobStatus} status
 * @property {number} order
 * @property {string} createdAt - ISO timestamp
 * @property {string} updatedAt - ISO timestamp
 */

/**
 * @typedef {Object} ExportPayload
 * @property {number} version
 * @property {string} exportedAt
 * @property {Job[]} jobs
 * @property {string[]} resumes
 */

export {}
