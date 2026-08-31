// ---------------------------------------------------------------------------
// Knowledge Base Entries domain (Postgres-backed persistence layer)
// ---------------------------------------------------------------------------

export type EntryType = 'documentation' | 'requirement' | 'constraint' | 'example' | 'other'

export type KnowledgeKind =
  | 'policy' | 'engineering_rule' | 'architecture_pattern' | 'testing_standard'
  | 'validation_rule' | 'task_playbook' | 'failure_pattern' | 'repair_playbook'
  | 'context_selection' | 'tool_knowledge' | 'documentation'

export type KnowledgeOwnerScope = 'global' | 'tenant' | 'workspace' | 'repository'

export type ComponentName =
  'ingestion' | 'storage' | 'retrieval' | 'embedding' | 'api' | 'admin' | 'unknown'

/** Full lifecycle status set (used for the edit form). */
export type EntryStatus =
  | 'open'
  | 'resolved'
  | 'deferred'
  | 'superseded'
  | 'draft'
  | 'pending_review'
  | 'published'
  | 'archived'
  | 'rejected'

/** Allowed values for PATCH /entries/{id} — a narrower subset of EntryStatus. */
export type EntryPatchStatus = 'open' | 'resolved' | 'deferred' | 'superseded'

export type Tag = {
  id: string
  name: string
  created_at: string
  updated_at: string
}

export type Entry = {
  id: string
  type: EntryType
  component: ComponentName
  title: string
  content: string
  source: string | null
  author: string
  status: EntryStatus
  created_at: string
  updated_at: string
  workstream_id?: string | null
  owner_scope?: KnowledgeOwnerScope
  tenant_id?: string | null
  workspace_id?: string | null
  repository_id?: string | null
  knowledge_kind?: KnowledgeKind
  applies_to?: string | null
  priority?: number
  tags: Tag[]
}

export type SearchResultItem = Entry & {
  similarity: number
}

export type EntrySearchResponse = {
  query: string
  results: SearchResultItem[]
  count: number
}

export type EntryListResponse = {
  entries: Entry[]
  total: number
  limit: number
  offset: number
}

export type EntryListFilters = {
  workstream_id?: string
  unassigned?: boolean
  component?: ComponentName
  type?: EntryType
  status?: EntryPatchStatus
  tag?: string
  limit?: number
  offset?: number
}

export type EntrySearchFilters = {
  workstream_id?: string
  unassigned?: boolean
  component?: ComponentName
  type?: EntryType
  status?: EntryPatchStatus
  tag?: string
  limit?: number
}

export type EntryCreatePayload = {
  type: EntryType
  component: ComponentName
  title: string
  content: string
  source?: string
  author: string
  workstream_id?: string | null
  owner_scope?: KnowledgeOwnerScope
  tenant_id?: string | null
  workspace_id?: string | null
  repository_id?: string | null
  knowledge_kind?: KnowledgeKind
  applies_to?: string | null
  priority?: number
}

export type EntryUpdatePayload = {
  type: EntryType
  component: ComponentName
  title: string
  content: string
  source?: string | null
  author: string
  status: EntryStatus
  workstream_id?: string | null
  owner_scope?: KnowledgeOwnerScope
  tenant_id?: string | null
  workspace_id?: string | null
  repository_id?: string | null
  knowledge_kind?: KnowledgeKind
  applies_to?: string | null
  priority?: number
}

export type JiraChildIssue = {
  key: string
  title: string
  status: string
  story_points: number | null
  browse_url: string
}

export type JiraLink = {
  jira_key: string
  title: string | null
  status: string | null
  issue_type: string | null
  story_points: number | null
  browse_url: string | null
  is_epic: boolean
  child_issues: JiraChildIssue[]
  enrichment_error: string | null
}

export type JiraLinksListResponse = {
  entry_id: string
  links: JiraLink[]
  count: number
}

export type Template = {
  id: string
  name: string
  content: string
  created_at: string
  updated_at: string
}
