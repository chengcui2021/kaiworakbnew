// Values aligned with backend/app/persistence/models.py enums.
import type { ComponentName, EntryPatchStatus, EntryStatus, EntryType } from '@/types/entry'

/**
 * Reka UI's Select forbids an empty-string `SelectItem` value (it's reserved
 * to mean "cleared" internally), so "any/none" options below use this
 * sentinel instead. Components using these options must translate it back
 * to `''`/`undefined` at the point they read the selected value.
 */
export const UNSET_OPTION = '__unset__'

export const ENTRY_TYPES: EntryType[] = [
  'documentation',
  'requirement',
  'constraint',
  'example',
  'other',
]

export const COMPONENTS: ComponentName[] = [
  'ingestion',
  'storage',
  'retrieval',
  'embedding',
  'api',
  'admin',
  'unknown',
]

export const SOURCES: Array<{ value: string; label: string }> = [
  { value: UNSET_OPTION, label: '— none —' },
  { value: 'manual submission', label: 'manual submission' },
  { value: 'meeting notes', label: 'meeting notes' },
  { value: 'test outcome', label: 'test outcome' },
  { value: 'code review', label: 'code review' },
  { value: 'incident postmortem', label: 'incident postmortem' },
  { value: 'design decision', label: 'design decision' },
  { value: 'open question', label: 'open question' },
]

/** PATCH /entries/{id} — lifecycle statuses only. */
export const PATCH_STATUSES: EntryPatchStatus[] = ['open', 'resolved', 'deferred', 'superseded']

/** Publish-style statuses — a separate family from the lifecycle set above. */
export const PUBLISH_STATUSES: EntryStatus[] = [
  'draft',
  'pending_review',
  'published',
  'archived',
  'rejected',
]

/** All statuses across both families (for the edit form). */
export const ALL_STATUSES: EntryStatus[] = [...PATCH_STATUSES, ...PUBLISH_STATUSES]

/** Common filters for list + search (same lifecycle set used for PATCH). */
export const FILTER_STATUSES: Array<{ value: string; label: string }> = [
  { value: UNSET_OPTION, label: 'Any status' },
  ...PATCH_STATUSES.map((s) => ({ value: s, label: s })),
]

export const FILTER_TYPES: Array<{ value: string; label: string }> = [
  { value: UNSET_OPTION, label: 'Any type' },
  ...ENTRY_TYPES.map((t) => ({ value: t, label: t })),
]

export const FILTER_COMPONENTS: Array<{ value: string; label: string }> = [
  { value: UNSET_OPTION, label: 'Any component' },
  ...COMPONENTS.map((c) => ({ value: c, label: c })),
]
