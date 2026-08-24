import technicalSpecification from '@/assets/document-templates/technical-specification-template.md?raw'
import meetingMinutes from '@/assets/document-templates/meeting-minutes-template.md?raw'
import reviewerFeedback from '@/assets/document-templates/reviewer-feedback-template.md?raw'

export interface DocumentTemplate {
  value: string
  label: string
  content: string
}

export const DOCUMENT_TEMPLATES: DocumentTemplate[] = [
  {
    value: 'technical-specification',
    label: 'Technical Specification',
    content: technicalSpecification,
  },
  { value: 'meeting-minutes', label: 'Meeting Minutes', content: meetingMinutes },
  { value: 'developer-review', label: 'Developer Review', content: reviewerFeedback },
]
