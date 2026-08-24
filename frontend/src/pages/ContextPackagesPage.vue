<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { AlertCircle, AlertTriangle, PackageCheck } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { usePackageService } from '../services/usePackageService'
import { useDocumentService } from '../services/useDocumentService'
import { useEntryService } from '@/services/useEntryService'
import { useWorkspace } from '../composables/useWorkspace'
import {
  emptyGovernedContextInputs,
  useContextAssemblyLock,
} from '../composables/useContextAssemblyLock'
import { formatDateTime } from '../utils/format'
import type { ContextPackage, KbDocument } from '../types/domain'
import type { GovernedContextInputs } from '../composables/useContextAssemblyLock'
import ContextHash from '../components/ContextHash.vue'
import ApprovalBadge from '../components/ApprovalBadge.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'

type ApprovedItem = KbDocument & { source: 'workspace' | 'entry' }

const { activeWorkspace } = useWorkspace()
const { createContextPackage, listContextPackages } = usePackageService()
const { listDocuments } = useDocumentService()
const { listEntries } = useEntryService()

const approvedEntries = ref<ApprovedItem[]>([])
const packages = ref<ContextPackage[]>([])
const selected = ref<Set<string>>(new Set())
const name = ref('')
const loadError = ref<string | null>(null)
const busy = ref(false)
const loading = ref(false)

const canCreate = computed(() => !!name.value.trim() && selected.value.size > 0 && !busy.value)

const workspaceApprovedEntries = computed(() =>
  approvedEntries.value.filter((doc) => doc.source === 'workspace')
)
const resolvedKbEntries = computed(() =>
  approvedEntries.value.filter((doc) => doc.source === 'entry')
)

const entryFilter = ref('')
const filteredWorkspaceApprovedEntries = computed(() => {
  const q = entryFilter.value.trim().toLowerCase()
  if (!q) return workspaceApprovedEntries.value
  return workspaceApprovedEntries.value.filter((doc) => doc.title.toLowerCase().includes(q))
})
const filteredResolvedKbEntries = computed(() => {
  const q = entryFilter.value.trim().toLowerCase()
  if (!q) return resolvedKbEntries.value
  return resolvedKbEntries.value.filter((doc) => doc.title.toLowerCase().includes(q))
})

// Context Assembly Lock export. The lock is produced by the backend governed
// context contract (`/api/governed-context/lock`) so it carries a deterministic
// context hash and the governed inputs it was built from — it is never
// assembled in the browser.
const {
  lock: contextLock,
  exporting: lockExporting,
  errors: lockErrors,
  exportContextLock: lockGovernedContext,
  reset: resetContextLock,
} = useContextAssemblyLock()
const governedInputs = ref<GovernedContextInputs>(emptyGovernedContextInputs())

// The first approved context package (if any) is eligible for lock export.
const approvedPackage = computed<ContextPackage | null>(
  () => packages.value.find((p) => p.approval_status === 'approved') ?? null
)

function titleFor(id: string): string {
  return approvedEntries.value.find((d) => d.id === id)?.title || id
}

async function exportContextLock() {
  const pkg = approvedPackage.value
  if (!pkg) return
  const created = await lockGovernedContext(pkg, governedInputs.value)
  if (created) toast.success(`Context assembly lock ${created.lock_id} exported.`)
  else if (lockErrors.value.length) toast.error(lockErrors.value[0])
}

function toggle(id: string) {
  const next = new Set(selected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selected.value = next
}

async function load() {
  loadError.value = null
  if (!activeWorkspace.value) {
    approvedEntries.value = []
    packages.value = []
    return
  }
  loading.value = true
  try {
    const ws = activeWorkspace.value.id
    // Only approved entries are eligible for packaging.
    const workspaceApproved = await listDocuments(ws, 'approved')
    const resolvedEntries = await listEntries({ status: 'resolved' })
    const persistentApproved: ApprovedItem[] = resolvedEntries.entries.map((entry) => ({
      id: entry.id,
      workspace_id: ws,
      title: entry.title,
      content: entry.content,
      created_at: entry.created_at,
      updated_at: entry.updated_at,
      approval_status: 'approved',
      approved_at: entry.updated_at,
      source: 'entry',
    }))
    approvedEntries.value = [
      ...workspaceApproved.map((doc): ApprovedItem => ({ ...doc, source: 'workspace' })),
      ...persistentApproved,
    ]
    packages.value = await listContextPackages(ws)
    // Drop any selections that are no longer approved/available.
    selected.value = new Set(
      [...selected.value].filter((id) => approvedEntries.value.some((d) => d.id === id))
    )
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : 'Failed to load packages'
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!activeWorkspace.value || !canCreate.value) return
  busy.value = true
  try {
    const pkg = await createContextPackage(activeWorkspace.value.id, {
      name: name.value.trim(),
      selected_entry_ids: [...selected.value],
    })
    toast.success(`Created package "${pkg.name}" with hash ${pkg.context_hash}.`)
    name.value = ''
    selected.value = new Set()
    await load()
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Failed to create package')
  } finally {
    busy.value = false
  }
}

onMounted(load)
watch(
  () => activeWorkspace.value?.id,
  () => {
    // A lock belongs to the workspace it was assembled from — never carry one
    // across a workspace switch.
    resetContextLock()
    load()
  }
)
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h2 class="flex items-center gap-2 text-2xl font-semibold">
        <PackageCheck class="size-6" aria-hidden="true" />
        Context Packages
      </h2>
      <p class="mt-1 text-muted-foreground">
        Bundle approved knowledge into an immutable, hash-verified package for downstream use (e.g.
        RAG pipelines). Each package carries a deterministic SHA256 integrity hash.
      </p>
    </div>

    <Alert v-if="!activeWorkspace" variant="warning" data-test="no-workspace">
      <AlertTriangle class="size-4" aria-hidden="true" />
      <AlertTitle>No workspace selected</AlertTitle>
      <AlertDescription> Choose one from the header to manage its packages. </AlertDescription>
    </Alert>

    <template v-else>
      <p class="text-sm text-muted-foreground" data-test="packages-scope">
        Workspace: <strong>{{ activeWorkspace.name }}</strong> ({{ activeWorkspace.id }})
      </p>

      <Alert v-if="loadError" variant="destructive" role="alert">
        <AlertCircle class="size-4" aria-hidden="true" />
        <AlertTitle>Couldn't load packages</AlertTitle>
        <AlertDescription>{{ loadError }}</AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle>Create Context Package</CardTitle>
        </CardHeader>
        <CardContent>
          <form class="grid gap-4" @submit.prevent="submit">
            <div class="grid gap-2">
              <Label for="package-name">Package name <em>(required)</em></Label>
              <Input
                id="package-name"
                v-model="name"
                required
                placeholder="e.g. Q1 Product Launch Context"
                data-test="package-name"
              />
            </div>

            <div class="grid gap-2">
              <Label for="package-workspace">Workspace</Label>
              <Input
                id="package-workspace"
                :model-value="activeWorkspace.name"
                readonly
                data-test="package-workspace"
              />
            </div>

            <div class="grid gap-3">
              <Label
                >Approved KB entries
                <em>(workspace approved entries and resolved KB entries are selectable)</em></Label
              >

              <div
                v-if="approvedEntries.length"
                class="grid gap-3"
                data-test="package-entry-picker"
              >
                <Input
                  v-model="entryFilter"
                  type="search"
                  placeholder="Filter entries by title…"
                  class="max-w-sm"
                  data-test="package-entry-filter"
                />

                <div v-if="filteredWorkspaceApprovedEntries.length" class="grid gap-1.5">
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-semibold uppercase text-muted-foreground"
                      >Workspace documents</span
                    >
                    <Badge variant="outline">{{ filteredWorkspaceApprovedEntries.length }}</Badge>
                  </div>
                  <ul class="flex flex-col gap-1.5">
                    <li v-for="doc in filteredWorkspaceApprovedEntries" :key="doc.id">
                      <label class="flex items-center gap-2">
                        <Checkbox
                          :checked="selected.has(doc.id)"
                          :data-test="`package-pick-${doc.id}`"
                          @update:checked="toggle(doc.id)"
                        />
                        <span class="text-sm font-medium">{{ doc.title }}</span>
                        <ApprovalBadge status="approved" />
                      </label>
                    </li>
                  </ul>
                </div>

                <div v-if="filteredResolvedKbEntries.length" class="grid gap-1.5">
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-semibold uppercase text-muted-foreground"
                      >Resolved KB entries</span
                    >
                    <Badge variant="outline">{{ filteredResolvedKbEntries.length }}</Badge>
                  </div>
                  <ul class="flex flex-col gap-1.5">
                    <li v-for="doc in filteredResolvedKbEntries" :key="doc.id">
                      <label class="flex items-center gap-2">
                        <Checkbox
                          :checked="selected.has(doc.id)"
                          :data-test="`package-pick-${doc.id}`"
                          @update:checked="toggle(doc.id)"
                        />
                        <span class="text-sm font-medium">{{ doc.title }}</span>
                        <ApprovalBadge status="approved" />
                      </label>
                    </li>
                  </ul>
                </div>

                <p
                  v-if="
                    entryFilter &&
                    !filteredWorkspaceApprovedEntries.length &&
                    !filteredResolvedKbEntries.length
                  "
                  class="text-sm text-muted-foreground"
                  data-test="package-entry-filter-empty"
                >
                  No entries match "{{ entryFilter }}".
                </p>
              </div>
              <p v-else class="text-sm text-muted-foreground" data-test="no-approved">
                No approved or resolved entries yet — approve a workspace document or mark a KB
                entry as resolved first.
              </p>
            </div>

            <div class="flex items-center gap-3">
              <Button type="submit" :disabled="!canCreate" data-test="package-create">
                {{ busy ? 'Creating…' : 'Create Package' }}
              </Button>
              <span class="text-sm text-muted-foreground"
                >{{ selected.size }} entr{{ selected.size === 1 ? 'y' : 'ies' }} selected</span
              >
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader class="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Packages ({{ packages.length }})</CardTitle>
            <p class="mt-1 text-xs text-muted-foreground">
              Packages are approved-by-construction — only pre-approved workspace documents and
              resolved KB entries were selectable above, so Export Context Lock requires no separate
              manual review step.
            </p>
          </div>
          <Button
            v-if="approvedPackage"
            variant="outline"
            size="sm"
            :disabled="lockExporting"
            data-test="export-context-lock"
            @click="exportContextLock"
          >
            Export Context Lock
          </Button>
        </CardHeader>
        <CardContent>
          <div
            v-if="approvedPackage"
            class="mb-4 grid gap-3 rounded-lg border border-dashed p-4"
            data-test="governed-context-inputs"
          >
            <div>
              <h3 class="text-sm font-semibold">Governed context inputs</h3>
              <p class="mt-1 text-xs text-muted-foreground">
                The lock is assembled by the backend from the engineering request, the repository
                (metadata only — the repository is never modified), the approved KB knowledge in
                <strong>{{ approvedPackage.name }}</strong> and the governance rules below.
              </p>
            </div>

            <div class="grid gap-3 sm:grid-cols-2">
              <div class="grid gap-1.5">
                <Label for="governed-request-title">Engineering request title</Label>
                <Input
                  id="governed-request-title"
                  v-model="governedInputs.requestTitle"
                  placeholder="e.g. Add infusion rate guard"
                  data-test="governed-request-title"
                />
              </div>
              <div class="grid gap-1.5">
                <Label for="governed-repo-name">Repository</Label>
                <Input
                  id="governed-repo-name"
                  v-model="governedInputs.repositoryName"
                  placeholder="e.g. metamorphic-kb"
                  data-test="governed-repo-name"
                />
              </div>
              <div class="grid gap-1.5">
                <Label for="governed-repo-branch">Branch <em>(optional)</em></Label>
                <Input
                  id="governed-repo-branch"
                  v-model="governedInputs.repositoryBranch"
                  placeholder="e.g. main"
                  data-test="governed-repo-branch"
                />
              </div>
              <div class="grid gap-1.5">
                <Label for="governed-repo-commit">Commit SHA</Label>
                <Input
                  id="governed-repo-commit"
                  v-model="governedInputs.repositoryCommitSha"
                  placeholder="e.g. 482c532"
                  data-test="governed-repo-commit"
                />
              </div>
            </div>

            <div class="grid gap-1.5">
              <Label for="governed-request-description">Engineering request description</Label>
              <Textarea
                id="governed-request-description"
                v-model="governedInputs.requestDescription"
                rows="2"
                placeholder="What the downstream run has to build."
                data-test="governed-request-description"
              />
            </div>

            <div class="grid gap-1.5">
              <Label for="governed-governance"
                >Engineering governance <em>(one “topic :: rule” per line, optional)</em></Label
              >
              <Textarea
                id="governed-governance"
                v-model="governedInputs.governance"
                rows="2"
                placeholder="logging :: Log every dose change."
                data-test="governed-governance"
              />
            </div>

            <Alert
              v-if="lockErrors.length"
              variant="destructive"
              role="alert"
              data-test="governed-lock-errors"
            >
              <AlertCircle class="size-4" aria-hidden="true" />
              <AlertTitle>Context assembly lock rejected</AlertTitle>
              <AlertDescription>
                <ul class="ml-4 list-disc">
                  <li v-for="problem in lockErrors" :key="problem">{{ problem }}</li>
                </ul>
              </AlertDescription>
            </Alert>

            <div v-if="contextLock" class="grid gap-1.5" data-test="governed-lock-summary">
              <span class="text-xs uppercase text-muted-foreground"
                >Context assembly lock {{ contextLock.lock_id }}</span
              >
              <ContextHash :hash="contextLock.context_hash" :truncate="true" />
              <p class="text-xs text-muted-foreground">
                Governed inputs: commit
                {{ contextLock.governed_inputs.repository_commit_sha }},
                {{ contextLock.governed_inputs.knowledge_entry_ids.length }} approved KB entr{{
                  contextLock.governed_inputs.knowledge_entry_ids.length === 1 ? 'y' : 'ies'
                }}, {{ contextLock.governed_inputs.governance_rule_ids.length }} governance rule{{
                  contextLock.governed_inputs.governance_rule_ids.length === 1 ? '' : 's'
                }}.
              </p>
            </div>
          </div>

          <p v-if="loading" class="text-sm text-muted-foreground">Loading…</p>
          <ul v-else-if="packages.length" class="flex flex-col gap-4" data-test="package-list">
            <li
              v-for="pkg in packages"
              :key="pkg.id"
              class="rounded-lg border p-4"
              :data-test="`package-${pkg.id}`"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="font-semibold">{{ pkg.name }}</span>
                <ApprovalBadge :status="pkg.approval_status" />
              </div>
              <dl class="my-3 flex flex-wrap gap-6">
                <div>
                  <dt class="text-xs uppercase text-muted-foreground">Workspace</dt>
                  <dd class="text-sm font-medium">{{ pkg.workspace_id }}</dd>
                </div>
                <div>
                  <dt class="text-xs uppercase text-muted-foreground">Created</dt>
                  <dd class="text-sm font-medium">{{ formatDateTime(pkg.created_at) }}</dd>
                </div>
                <div>
                  <dt class="text-xs uppercase text-muted-foreground">Entries</dt>
                  <dd class="text-sm font-medium">{{ pkg.selected_entry_ids.length }}</dd>
                </div>
              </dl>
              <div class="text-sm">
                <span class="text-xs uppercase text-muted-foreground">Selected KB entries:</span>
                <ul class="ml-4 list-disc">
                  <li v-for="(id, idx) in pkg.selected_entry_ids" :key="id">
                    {{ pkg.entry_titles[idx] || titleFor(id) }}
                    <code class="text-xs text-muted-foreground">({{ id }})</code>
                  </li>
                </ul>
              </div>
              <div class="mt-3 border-t border-dashed pt-3">
                <span class="mb-1 block text-xs uppercase text-muted-foreground"
                  >Context hash (integrity):</span
                >
                <ContextHash :hash="pkg.context_hash" :truncate="true" />
              </div>
            </li>
          </ul>
          <p v-else class="text-sm text-muted-foreground" data-test="package-empty">
            No context packages yet. Create one above from approved entries.
          </p>
        </CardContent>
      </Card>
    </template>
  </div>
</template>
