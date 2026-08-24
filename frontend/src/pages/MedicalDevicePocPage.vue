<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { AlertCircle, AlertTriangle, CheckCircle2, Stethoscope } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { usePackageService } from '../services/usePackageService'
import { useDocumentService } from '../services/useDocumentService'
import { useWorkspaceService } from '../services/useWorkspaceService'
import { useWorkspace } from '../composables/useWorkspace'
import { formatDateTime } from '../utils/format'
import type { ContextPackage, KbDocument, WorkspaceValidationResult } from '../types/domain'
import ContextHash from '../components/ContextHash.vue'
import ApprovalBadge from '../components/ApprovalBadge.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

// ---------------------------------------------------------------------------
// Medical Device POC — a thin, frontend-only slice that walks an operator
// through the end-to-end regulated workflow using the existing KB APIs:
//   1. select an active workspace        (header WorkspaceIndicator + useWorkspace)
//   2. view approved knowledge entries    (listDocuments approved)
//   3. create a context package           (createContextPackage)
//   4. export the context assembly lock   (mirrors ContextPackagesPage behaviour)
//   5. "Ready for Project Run" handoff     (Jira / GitHub / preview / validation)
// It does not change any existing page or the Context Package export behaviour.
// ---------------------------------------------------------------------------

const { activeWorkspace } = useWorkspace()
const { createContextPackage, listContextPackages } = usePackageService()
const { listDocuments } = useDocumentService()
const { validateWorkspace } = useWorkspaceService()

const approvedEntries = ref<KbDocument[]>([])
const packages = ref<ContextPackage[]>([])
const selected = ref<Set<string>>(new Set())
const name = ref('')
const loading = ref(false)
const busy = ref(false)
const loadError = ref<string | null>(null)

// The package this POC run created/locked. Drives steps 4 & 5.
const pocPackage = ref<ContextPackage | null>(null)
const lockExported = ref(false)
const validation = ref<WorkspaceValidationResult | null>(null)
const validating = ref(false)

// Context Assembly Lock export — same shape emitted by ContextPackagesPage.
const CONTEXT_LOCK_VERSION = '1.0'

const canCreate = computed(() => !!name.value.trim() && selected.value.size > 0 && !busy.value)

function titleFor(id: string): string {
  return approvedEntries.value.find((d) => d.id === id)?.title || id
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
    approvedEntries.value = await listDocuments(ws, 'approved')
    packages.value = await listContextPackages(ws)
    selected.value = new Set(
      [...selected.value].filter((id) => approvedEntries.value.some((d) => d.id === id))
    )
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : 'Failed to load workspace data'
  } finally {
    loading.value = false
  }
}

async function createPackage() {
  if (!activeWorkspace.value || !canCreate.value) return
  busy.value = true
  try {
    const pkg = await createContextPackage(activeWorkspace.value.id, {
      name: name.value.trim(),
      selected_entry_ids: [...selected.value],
    })
    pocPackage.value = pkg
    lockExported.value = false
    toast.success(`Created context package "${pkg.name}" with hash ${pkg.context_hash}.`)
    name.value = ''
    selected.value = new Set()
    await load()
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Failed to create context package')
  } finally {
    busy.value = false
  }
}

function exportContextLock() {
  const pkg = pocPackage.value
  if (!pkg) return
  const lock = {
    lock_type: 'context_assembly_lock',
    version: CONTEXT_LOCK_VERSION,
    generated_at: new Date().toISOString(),
    approved_context_id: pkg.id,
    source_lineage: {
      workspace_id: pkg.workspace_id,
      package_id: pkg.id,
      package_name: pkg.name,
      context_hash: pkg.context_hash,
      entries: pkg.selected_entry_ids.map((id, idx) => ({
        id,
        title: pkg.entry_titles[idx] || titleFor(id),
      })),
    },
    // Placeholder: the real integrity checksum is computed downstream.
    checksum: 'sha256:PLACEHOLDER',
  }
  const blob = new Blob([JSON.stringify(lock, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'context-assembly-lock.json'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  lockExported.value = true
}

async function runValidation() {
  if (!activeWorkspace.value) return
  validating.value = true
  try {
    validation.value = await validateWorkspace(activeWorkspace.value.id)
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Validation failed')
    validation.value = null
  } finally {
    validating.value = false
  }
}

// Step completion flags drive the progress indicators.
const step1Done = computed(() => !!activeWorkspace.value)
const step2Done = computed(() => approvedEntries.value.length > 0)
const step3Done = computed(() => !!pocPackage.value)
const step4Done = computed(() => lockExported.value)
const handoffReady = computed(() => step3Done.value && step4Done.value)

const HANDOFF_VALUE_CLASS: Record<string, string> = {
  pass: 'font-semibold text-success',
  fail: 'font-semibold text-destructive',
  warning: 'font-semibold text-warning',
}

function resetRun() {
  pocPackage.value = null
  lockExported.value = false
  validation.value = null
  selected.value = new Set()
  name.value = ''
}

onMounted(load)
watch(
  () => activeWorkspace.value?.id,
  () => {
    resetRun()
    load()
  }
)
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h2 class="flex items-center gap-2 text-2xl font-semibold">
        <Stethoscope class="size-6" aria-hidden="true" />
        Medical Device POC
      </h2>
      <p class="mt-1 text-muted-foreground">
        End-to-end regulated workflow slice: select a workspace, review approved knowledge, assemble
        a hash-verified context package, lock it, and hand it off for a Project Run. This is a
        demonstration slice — it reuses the existing KB APIs and does not change them.
      </p>
    </div>

    <Alert v-if="loadError" variant="destructive" role="alert">
      <AlertCircle class="size-4" aria-hidden="true" />
      <AlertTitle>Couldn't load workspace data</AlertTitle>
      <AlertDescription>{{ loadError }}</AlertDescription>
    </Alert>

    <!-- Step 1: select an active workspace -->
    <Card :class="{ 'border-success': step1Done }" data-test="mdp-step-1">
      <CardHeader>
        <CardTitle class="flex items-center">
          <span
            class="mr-2 inline-flex size-6 items-center justify-center rounded-full text-sm font-bold"
            :class="
              step1Done ? 'bg-success text-success-foreground' : 'bg-muted text-muted-foreground'
            "
            >1</span
          >
          Select an active workspace
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p v-if="activeWorkspace" class="text-sm text-muted-foreground" data-test="mdp-workspace">
          Active: <strong>{{ activeWorkspace.name }}</strong> ({{ activeWorkspace.id }})
        </p>
        <Alert v-else variant="warning" data-test="mdp-no-workspace">
          <AlertTriangle class="size-4" aria-hidden="true" />
          <AlertTitle>No workspace selected</AlertTitle>
          <AlertDescription>
            Choose one from the “Active Workspace” picker in the header.
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>

    <template v-if="activeWorkspace">
      <div class="ml-9 h-4 w-px bg-border" aria-hidden="true" data-test="mdp-step-connector" />

      <!-- Step 2: view approved knowledge entries -->
      <Card :class="{ 'border-success': step2Done }" data-test="mdp-step-2">
        <CardHeader>
          <CardTitle class="flex items-center">
            <span
              class="mr-2 inline-flex size-6 items-center justify-center rounded-full text-sm font-bold"
              :class="
                step2Done ? 'bg-success text-success-foreground' : 'bg-muted text-muted-foreground'
              "
              >2</span
            >
            Approved knowledge entries
          </CardTitle>
        </CardHeader>
        <CardContent class="flex flex-col gap-2">
          <p class="text-sm text-muted-foreground">
            Only approved entries are eligible for a regulated context package.
          </p>
          <p v-if="loading" class="text-sm text-muted-foreground">Loading…</p>
          <ul
            v-else-if="approvedEntries.length"
            class="flex flex-col gap-1.5"
            data-test="mdp-approved-list"
          >
            <li v-for="doc in approvedEntries" :key="doc.id">
              <label class="flex items-center gap-2">
                <Checkbox
                  :checked="selected.has(doc.id)"
                  :data-test="`mdp-pick-${doc.id}`"
                  @update:checked="toggle(doc.id)"
                />
                <span class="text-sm font-medium">{{ doc.title }}</span>
                <ApprovalBadge status="approved" />
              </label>
            </li>
          </ul>
          <p v-else class="text-sm text-muted-foreground" data-test="mdp-no-approved">
            No approved entries in this workspace yet — approve some on the workspace page first.
          </p>
        </CardContent>
      </Card>

      <div class="ml-9 h-4 w-px bg-border" aria-hidden="true" data-test="mdp-step-connector" />

      <!-- Step 3: create a context package -->
      <Card :class="{ 'border-success': step3Done }" data-test="mdp-step-3">
        <CardHeader>
          <CardTitle class="flex items-center">
            <span
              class="mr-2 inline-flex size-6 items-center justify-center rounded-full text-sm font-bold"
              :class="
                step3Done ? 'bg-success text-success-foreground' : 'bg-muted text-muted-foreground'
              "
              >3</span
            >
            Create a context package
          </CardTitle>
        </CardHeader>
        <CardContent class="flex flex-col gap-3">
          <form class="grid gap-4" @submit.prevent="createPackage">
            <div class="grid gap-2">
              <Label for="mdp-package-name">Package name <em>(required)</em></Label>
              <Input
                id="mdp-package-name"
                v-model="name"
                required
                placeholder="e.g. Infusion Pump v2 — Regulated Context"
                data-test="mdp-package-name"
              />
            </div>
            <div class="flex items-center gap-3">
              <Button type="submit" :disabled="!canCreate" data-test="mdp-create-package">
                {{ busy ? 'Creating…' : 'Create Context Package' }}
              </Button>
              <span class="text-sm text-muted-foreground"
                >{{ selected.size }} entr{{ selected.size === 1 ? 'y' : 'ies' }} selected</span
              >
            </div>
          </form>
        </CardContent>
      </Card>

      <div class="ml-9 h-4 w-px bg-border" aria-hidden="true" data-test="mdp-step-connector" />

      <!-- Step 4: export the context assembly lock -->
      <Card :class="{ 'border-success': step4Done }" data-test="mdp-step-4">
        <CardHeader>
          <CardTitle class="flex items-center">
            <span
              class="mr-2 inline-flex size-6 items-center justify-center rounded-full text-sm font-bold"
              :class="
                step4Done ? 'bg-success text-success-foreground' : 'bg-muted text-muted-foreground'
              "
              >4</span
            >
            Export the context assembly lock
          </CardTitle>
        </CardHeader>
        <CardContent>
          <template v-if="pocPackage">
            <dl class="mb-3 flex flex-wrap gap-6">
              <div>
                <dt class="text-xs uppercase text-muted-foreground">Package</dt>
                <dd class="text-sm font-medium">{{ pocPackage.name }}</dd>
              </div>
              <div>
                <dt class="text-xs uppercase text-muted-foreground">Created</dt>
                <dd class="text-sm font-medium">{{ formatDateTime(pocPackage.created_at) }}</dd>
              </div>
              <div>
                <dt class="text-xs uppercase text-muted-foreground">Entries</dt>
                <dd class="text-sm font-medium">{{ pocPackage.selected_entry_ids.length }}</dd>
              </div>
            </dl>
            <div class="mb-3">
              <span class="mb-1 block text-xs uppercase text-muted-foreground"
                >Context hash (integrity):</span
              >
              <ContextHash :hash="pocPackage.context_hash" :truncate="true" />
            </div>
            <div class="flex items-center gap-3">
              <Button type="button" data-test="mdp-export-lock" @click="exportContextLock">
                {{ lockExported ? 'Re-export Context Lock' : 'Export Context Lock' }}
              </Button>
              <span
                v-if="lockExported"
                class="inline-flex items-center gap-1.5 text-sm text-muted-foreground"
                data-test="mdp-lock-exported"
              >
                <CheckCircle2 class="size-4 text-success" aria-hidden="true" />
                Context assembly lock exported.
              </span>
            </div>
          </template>
          <p v-else class="text-sm text-muted-foreground">
            Create a context package in step 3 to unlock the assembly lock export.
          </p>
        </CardContent>
      </Card>

      <div class="ml-9 h-4 w-px bg-border" aria-hidden="true" data-test="mdp-step-connector" />

      <!-- Step 5: Ready for Project Run handoff panel -->
      <Card :class="{ 'border-success': handoffReady }" data-test="mdp-step-5">
        <CardHeader>
          <CardTitle class="flex items-center">
            <span
              class="mr-2 inline-flex size-6 items-center justify-center rounded-full text-sm font-bold"
              :class="
                handoffReady
                  ? 'bg-success text-success-foreground'
                  : 'bg-muted text-muted-foreground'
              "
              >5</span
            >
            Ready for Project Run
          </CardTitle>
        </CardHeader>
        <CardContent class="flex flex-col gap-3">
          <Alert v-if="!handoffReady" variant="warning" data-test="mdp-handoff-blocked">
            <AlertTriangle class="size-4" aria-hidden="true" />
            <AlertTitle>Not ready yet</AlertTitle>
            <AlertDescription>
              Complete steps 3 and 4 to assemble the handoff package.
            </AlertDescription>
          </Alert>
          <template v-else>
            <Alert variant="success" data-test="mdp-handoff-ready">
              <CheckCircle2 class="size-4" aria-hidden="true" />
              <AlertTitle>Ready for Project Run</AlertTitle>
              <AlertDescription>
                Context locked for <strong>{{ pocPackage?.name }}</strong> — ready to hand off to a
                Project Run.
              </AlertDescription>
            </Alert>
            <ul
              class="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-2.5"
              data-test="mdp-handoff-grid"
            >
              <li class="flex flex-col gap-1 rounded-md border bg-muted/50 p-3">
                <span class="text-xs font-semibold uppercase text-muted-foreground"
                  >Jira ticket</span
                >
                <span class="text-sm italic text-muted-foreground"
                  >Not yet linked — paste ticket URL during Project Run</span
                >
              </li>
              <li class="flex flex-col gap-1 rounded-md border bg-muted/50 p-3">
                <span class="text-xs font-semibold uppercase text-muted-foreground">GitHub PR</span>
                <span class="text-sm italic text-muted-foreground"
                  >Not yet opened — created when the run produces a diff</span
                >
              </li>
              <li class="flex flex-col gap-1 rounded-md border bg-muted/50 p-3">
                <span class="text-xs font-semibold uppercase text-muted-foreground"
                  >Preview evidence</span
                >
                <span class="text-sm italic text-muted-foreground">Pending preview capture</span>
              </li>
              <li class="flex flex-col gap-1 rounded-md border bg-muted/50 p-3">
                <span class="text-xs font-semibold uppercase text-muted-foreground"
                  >Validation status</span
                >
                <span
                  v-if="validation"
                  class="text-sm"
                  :class="HANDOFF_VALUE_CLASS[validation.overall_status]"
                  data-test="mdp-validation-status"
                >
                  {{ validation.overall_status.toUpperCase() }}
                  — {{ validation.checks.length }} check{{
                    validation.checks.length === 1 ? '' : 's'
                  }}
                </span>
                <span v-else class="text-sm italic text-muted-foreground"> Not run yet </span>
              </li>
            </ul>
            <div class="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                :disabled="validating"
                data-test="mdp-run-validation"
                @click="runValidation"
              >
                {{ validating ? 'Validating…' : 'Run Workspace Validation' }}
              </Button>
              <Button variant="ghost" size="sm" data-test="mdp-reset" @click="resetRun">
                Start New Run
              </Button>
            </div>
          </template>
        </CardContent>
      </Card>
    </template>
  </div>
</template>
