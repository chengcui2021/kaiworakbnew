<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { toast } from 'vue-sonner'
import { Github, Loader2, ShieldCheck } from 'lucide-vue-next'
import { useIngestionService } from '@/services/useIngestionService'
import { useWorkstreamService } from '@/services/useWorkstreamService'
import type { Workstream } from '@/types/domain'
import type { GitHubIngestionResult } from '@/types/ingestion'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const { ingestGitHub, ingestText, ingestUrl } = useIngestionService()
const { listWorkstreams } = useWorkstreamService()
const workstreams = ref<Workstream[]>([])
const repositoryUrl = ref('')
const branch = ref('main')
const commitRef = ref('')
const workstreamId = ref('')
const author = ref('Knowledge Ingestion')
const includePaths = ref('**/*.md\n*.md\n**/CLAUDE.md\n**/AGENTS.md')
const excludePaths = ref('node_modules/**\ndist/**\nbuild/**\n.git/**')
const loading = ref(false)
const result = ref<GitHubIngestionResult | null>(null)
const textTitle = ref('')
const textContent = ref('')
const textSourceType = ref('manual')
const sourceUrl = ref('')
const sourceLoading = ref(false)

function lines(value: string): string[] {
  return value.split(/\r?\n/).map((x) => x.trim()).filter(Boolean)
}

async function submit() {
  if (!repositoryUrl.value.trim()) {
    toast.error('Repository URL is required')
    return
  }
  loading.value = true
  result.value = null
  try {
    result.value = await ingestGitHub({
      repository_url: repositoryUrl.value.trim(),
      branch: branch.value.trim() || 'main',
      ref: commitRef.value.trim() || null,
      include_paths: lines(includePaths.value),
      exclude_paths: lines(excludePaths.value),
      workstream_id: workstreamId.value || null,
      author: author.value.trim() || 'Knowledge Ingestion',
    })
    toast.success(`${result.value.candidate_count} candidate knowledge entries created`, {
      description: 'Candidates are OPEN and must be reviewed before becoming Approved Knowledge.',
    })
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Knowledge ingestion failed')
  } finally {
    loading.value = false
  }
}

async function submitText() {
  if (!textTitle.value.trim() || !textContent.value.trim()) { toast.error('Title and knowledge text are required'); return }
  sourceLoading.value = true
  try { await ingestText({ title:textTitle.value.trim(), content:textContent.value.trim(), source_label:'admin-manual', source_type:textSourceType.value, workstream_id:workstreamId.value || null, author:author.value.trim() || 'Knowledge Ingestion' }); toast.success('OPEN knowledge candidate created — review required'); textTitle.value=''; textContent.value='' }
  catch (err) { toast.error(err instanceof Error ? err.message : 'Text ingestion failed') } finally { sourceLoading.value=false }
}
async function submitUrl() {
  if (!sourceUrl.value.trim()) { toast.error('Source URL is required'); return }
  sourceLoading.value = true
  try { await ingestUrl({ url:sourceUrl.value.trim(), workstream_id:workstreamId.value || null, author:author.value.trim() || 'Knowledge Ingestion' }); toast.success('URL snapshot created as OPEN candidate — review required'); sourceUrl.value='' }
  catch (err) { toast.error(err instanceof Error ? err.message : 'URL ingestion failed') } finally { sourceLoading.value=false }
}

onMounted(async () => {
  try { workstreams.value = await listWorkstreams() } catch { workstreams.value = [] }
})
</script>

<template>
  <div class="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
    <div>
      <h1 class="text-2xl font-semibold tracking-tight">Knowledge Sources</h1>
      <p class="mt-1 text-sm text-muted-foreground">
        Manage approved engineering intelligence sources. Runtime ticket/repository/transcript analysis happens in the Agent; Admin KB only ingests, governs, resolves and approves reusable knowledge. Ingestion never auto-approves knowledge.
      </p>
    </div>

    <Card>
      <CardHeader>
        <div class="flex items-center gap-2"><Github class="size-5" /><CardTitle>GitHub Repository</CardTitle></div>
        <CardDescription>Import text/Markdown knowledge from an exact repository commit with source lineage.</CardDescription>
      </CardHeader>
      <CardContent class="space-y-5">
        <div class="grid gap-4 md:grid-cols-2">
          <div class="space-y-2 md:col-span-2"><Label>Repository URL</Label><Input v-model="repositoryUrl" placeholder="https://github.com/owner/repository" /></div>
          <div class="space-y-2"><Label>Branch</Label><Input v-model="branch" placeholder="main" /></div>
          <div class="space-y-2"><Label>Commit / Ref (optional)</Label><Input v-model="commitRef" placeholder="Use branch HEAD when blank" /></div>
          <div class="space-y-2">
            <Label>Workstream (optional)</Label>
            <Select v-model="workstreamId">
              <SelectTrigger><SelectValue placeholder="Unassigned" /></SelectTrigger>
              <SelectContent><SelectItem v-for="ws in workstreams" :key="ws.id" :value="ws.id">{{ ws.name }}</SelectItem></SelectContent>
            </Select>
          </div>
          <div class="space-y-2"><Label>Author</Label><Input v-model="author" /></div>
        </div>
        <div class="grid gap-4 md:grid-cols-2">
          <div class="space-y-2"><Label>Include paths (one glob per line)</Label><textarea v-model="includePaths" class="min-h-32 w-full rounded-md border bg-background px-3 py-2 font-mono text-sm" /></div>
          <div class="space-y-2"><Label>Exclude paths (one glob per line)</Label><textarea v-model="excludePaths" class="min-h-32 w-full rounded-md border bg-background px-3 py-2 font-mono text-sm" /></div>
        </div>
        <div class="rounded-md border bg-muted/30 p-3 text-sm text-muted-foreground">
          <div class="flex items-center gap-2 font-medium text-foreground"><ShieldCheck class="size-4" />Governed ingestion</div>
          <p class="mt-1">The source is resolved to an exact commit SHA. Extracted sections are created as OPEN candidates with repository, commit and source-file lineage. Review/Resolve remains a human action.</p>
        </div>
        <Button :disabled="loading" @click="submit"><Loader2 v-if="loading" class="mr-2 size-4 animate-spin" />{{ loading ? 'Analysing source…' : 'Analyse & Ingest' }}</Button>
      </CardContent>
    </Card>


    <div class="grid gap-6 md:grid-cols-2">
      <Card>
        <CardHeader><CardTitle>Manual / Pasted Knowledge</CardTitle><CardDescription>Add standards, playbooks, architecture decisions, validation rules or curated guidance. Always enters review as OPEN.</CardDescription></CardHeader>
        <CardContent class="space-y-3"><Select v-model="textSourceType"><SelectTrigger><SelectValue placeholder="Source type" /></SelectTrigger><SelectContent><SelectItem value="manual">Manual / curated</SelectItem><SelectItem value="claude_skill">Claude Skill</SelectItem><SelectItem value="claude_md">CLAUDE.md</SelectItem><SelectItem value="agents_md">AGENTS.md</SelectItem><SelectItem value="architecture">Architecture guidance</SelectItem><SelectItem value="validation_playbook">Validation playbook</SelectItem><SelectItem value="coding_standard">Coding standard</SelectItem><SelectItem value="security_policy">Security policy</SelectItem><SelectItem value="historical_pr">Historical PR evidence</SelectItem><SelectItem value="confluence">Confluence export</SelectItem><SelectItem value="notion">Notion export</SelectItem><SelectItem value="document">PDF / DOCX extracted text</SelectItem></SelectContent></Select><Input v-model="textTitle" placeholder="Knowledge title" /><textarea v-model="textContent" class="min-h-40 w-full rounded-md border bg-background px-3 py-2 text-sm" placeholder="Paste approved-source material or a curated candidate…" /><Button :disabled="sourceLoading" @click="submitText">Create review candidate</Button></CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Web / Documentation URL</CardTitle><CardDescription>Snapshot a text-based standards or documentation URL. The snapshot is not authoritative until reviewed and resolved.</CardDescription></CardHeader>
        <CardContent class="space-y-3"><Input v-model="sourceUrl" placeholder="https://docs.example.com/engineering-standard" /><Button :disabled="sourceLoading" @click="submitUrl">Snapshot & create candidate</Button></CardContent>
      </Card>
    </div>

    <Card>
      <CardHeader><CardTitle>Agent Run Learning</CardTitle><CardDescription>Kaiwora Agent runs automatically submit evidence-backed learning candidates into the relevant workstream. They appear with source <code>agent-run:…</code> and use the same human Resolve/Defer/Supersede lifecycle as all other entries.</CardDescription></CardHeader>
      <CardContent><div class="rounded-md border bg-muted/30 p-3 text-sm">Agent learning never auto-approves itself. Tenant-private observations stay private to the customer and become reusable only after customer review and approval.</div></CardContent>
    </Card>

    <Card v-if="result">
      <CardHeader><CardTitle>Ingestion Result</CardTitle><CardDescription>{{ result.repository_url }} @ {{ result.commit_sha.slice(0, 12) }}</CardDescription></CardHeader>
      <CardContent class="space-y-4">
        <div class="flex flex-wrap gap-2"><Badge variant="secondary">{{ result.scanned_files }} source files</Badge><Badge variant="secondary">{{ result.candidate_count }} candidates</Badge><Badge>OPEN — review required</Badge></div>
        <div class="divide-y rounded-md border">
          <div v-for="entry in result.candidates" :key="entry.id" class="flex items-start justify-between gap-4 p-3">
            <div class="min-w-0"><p class="font-medium">{{ entry.title }}</p><p class="mt-1 truncate text-xs text-muted-foreground">{{ entry.source }}</p></div>
            <Badge variant="outline">{{ entry.status }}</Badge>
          </div>
        </div>
        <Button variant="outline" as-child><RouterLink to="/browse">Review candidate knowledge</RouterLink></Button>
      </CardContent>
    </Card>
  </div>
</template>
