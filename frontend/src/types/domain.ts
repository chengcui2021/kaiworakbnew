// ---------------------------------------------------------------------------
// Knowledge Base / Workspace domain (Continue KB Phase 1.5)
// ---------------------------------------------------------------------------

export type Workspace = {
  id: string
  name: string
  description: string
  created_at: string
  updated_at: string
  document_count: number
}

export type ApprovalStatus = 'draft' | 'approved' | 'archived'

export type KbDocument = {
  id: string
  workspace_id: string
  title: string
  content: string
  created_at: string
  updated_at: string
  approval_status: ApprovalStatus | string
  approved_at?: string | null
}

export type ContextPackage = {
  id: string
  name: string
  workspace_id: string
  selected_entry_ids: string[]
  created_at: string
  approval_status: ApprovalStatus | string
  context_hash: string
  entry_titles: string[]
}

export type WorkspaceStats = {
  workspace_id: string
  document_count: number
  total_characters: number
  last_updated?: string | null
}

export type SearchResultItem = {
  document: KbDocument
  snippet: string
}

export type SearchResponse = {
  query: string
  workspace_id: string
  total: number
  results: SearchResultItem[]
}

export type ValidationStatus = 'pass' | 'fail' | 'warning'

export type ValidationCheck = {
  name: string
  label: string
  status: ValidationStatus
  message: string
  details?: Record<string, unknown>
}

export type WorkspaceValidationResult = {
  workspace_id: string
  workspace_name: string
  validated_at: string
  overall_status: ValidationStatus
  checks: ValidationCheck[]
}

export type ActivityEventType =
  | 'workspace_created'
  | 'workspace_renamed'
  | 'document_uploaded'
  | 'document_deleted'
  | 'document_moved'
  | 'document_approved'
  | 'document_archived'
  | 'document_drafted'
  | 'package_created'

export type WorkspaceActivity = {
  id: string
  workspace_id: string
  event_type: ActivityEventType | string
  timestamp: string
  description: string
  metadata?: Record<string, unknown>
}

export type Workstream = {
  id: string
  name: string
  description: string
  created_at: string
  updated_at: string
  entry_count: number
}

export type WorkstreamStats = {
  workstream_id: string
  entry_count: number
  total_characters: number
  last_updated?: string | null
}

export type WorkstreamValidationResult = {
  workstream_id: string
  workstream_name: string
  validated_at: string
  overall_status: ValidationStatus
  checks: ValidationCheck[]
}
