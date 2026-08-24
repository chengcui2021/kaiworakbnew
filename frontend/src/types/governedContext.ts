// ---------------------------------------------------------------------------
// Governed Context Assembly (MDSU-345, Phase 1)
//
// Mirrors the backend contract in `backend/app/schemas/context_assembly.py`,
// exposed at `/api/governed-context/*`. Field names are snake_case on purpose:
// these objects cross the wire verbatim, so renaming one here is a contract
// break, not a style choice.
// ---------------------------------------------------------------------------

// --- Inputs ----------------------------------------------------------------

export type EngineeringRequestInput = {
  id?: string
  title: string
  description: string
  acceptance_criteria?: string[]
  source?: string
}

export type RepositoryFileInput = {
  path: string
  language?: string
  role?: string
}

/**
 * Repository information supplied by the caller. Repository analysis is
 * metadata-only — the KB never clones, reads from, or writes to the target
 * repository.
 */
export type RepositoryInput = {
  name: string
  url?: string
  branch?: string
  commit_sha: string
  files?: RepositoryFileInput[]
}

export type KnowledgeSelectionInput = {
  entry_ids: string[]
}

export type GovernanceRuleInput = {
  id: string
  title: string
  topic: string
  rule: string
  source?: string
  status?: string
  precedence?: number
}

export type GovernedContextRequest = {
  request: EngineeringRequestInput
  repository: RepositoryInput
  knowledge: KnowledgeSelectionInput
  governance: GovernanceRuleInput[]
}

// --- Context sections ------------------------------------------------------

export type RequirementAnalysisContext = {
  request_id: string | null
  title: string
  description: string
  acceptance_criteria: string[]
  source: string | null
  digest: string
}

export type RepositoryFileContext = {
  path: string
  language: string | null
  role: string | null
}

export type RepositoryAnalysisContext = {
  name: string
  url: string | null
  branch: string | null
  commit_sha: string
  file_count: number
  languages: string[]
  top_level_paths: string[]
  files: RepositoryFileContext[]
  analysis_mode: string
  read_only: boolean
  digest: string
}

/** Source lineage for one KB-derived item. */
export type KnowledgeProvenance = {
  entry_id: string
  title: string
  source: string | null
  version: string | null
  updated_at: string | null
  status: string
}

export type KnowledgeContext = {
  source_capability: string
  approved_status: string
  entry_ids: string[]
  entry_count: number
  provenance: KnowledgeProvenance[]
  knowledge_hash: string
  digest: string
}

export type GovernanceRuleContext = {
  id: string
  title: string
  topic: string
  rule: string
  source: string | null
  precedence: number
}

export type GovernanceSupersession = {
  topic: string
  superseded_rule_id: string
  superseded_by_rule_id: string
}

export type EngineeringGovernanceContext = {
  rules: GovernanceRuleContext[]
  excluded_rule_ids: string[]
  superseded: GovernanceSupersession[]
  digest: string
}

// --- Assembly + lock -------------------------------------------------------

export type GovernedContextAssembly = {
  assembly_version: string
  requirement_context: RequirementAnalysisContext
  repository_context: RepositoryAnalysisContext
  knowledge_context: KnowledgeContext
  governance_context: EngineeringGovernanceContext
  input_digests: Record<string, string>
  context_hash: string
  created_at: string
}

/** Identifies the governed inputs a lock was produced from. */
export type GovernedInputsRef = {
  request_id: string | null
  request_digest: string
  repository_commit_sha: string
  repository_digest: string
  knowledge_entry_ids: string[]
  knowledge_hash: string
  governance_rule_ids: string[]
  governance_digest: string
}

export type ContextAssemblyLock = {
  lock_id: string
  assembly_version: string
  context_hash: string
  input_digests: Record<string, string>
  governed_inputs: GovernedInputsRef
  created_at: string
}

export type StalenessReason = {
  section: string
  reason: string
  locked_digest: string | null
  current_digest: string | null
}

export type LockStatusResponse = {
  lock_id: string
  stale: boolean
  locked_context_hash: string
  current_context_hash: string
  reasons: StalenessReason[]
}
