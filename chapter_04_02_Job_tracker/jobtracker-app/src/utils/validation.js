/**
 * @param {{company: string, title: string, linkedinUrl: string}} values
 */
export function validateJobForm(values) {
  const errors = {}

  if (!values.company || !values.company.trim()) {
    errors.company = 'Company name is required'
  }

  if (!values.title || !values.title.trim()) {
    errors.title = 'Job title is required'
  }

  if (values.linkedinUrl && values.linkedinUrl.trim()) {
    try {
      new URL(values.linkedinUrl.trim())
    } catch {
      errors.linkedinUrl = 'Enter a valid URL (include https://)'
    }
  }

  return { errors, isValid: Object.keys(errors).length === 0 }
}
