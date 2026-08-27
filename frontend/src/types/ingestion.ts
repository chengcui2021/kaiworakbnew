import type { Entry } from './entry'

export type GitHubIngestionPayload = {
  repository_url: string
  branch: string
  ref?: string | null
  include_paths: string[]
  exclude_paths: string[]
  workstream_id?: string | null
  author: string
}

export type GitHubIngestionResult = {
  repository_url: string
  branch: string
  commit_sha: string
  scanned_files: number
  candidate_count: number
  candidates: Entry[]
}
