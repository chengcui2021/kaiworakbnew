<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { AlertCircle } from 'lucide-vue-next'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import { Toaster } from '@/components/ui/sonner'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import ConfirmDialogHost from '@/components/ConfirmDialogHost.vue'
import { useWorkspace } from './composables/useWorkspace'
import { useWorkstream } from './composables/useWorkstream'

const { error, loadWorkspaces } = useWorkspace()
const { loadWorkstreams } = useWorkstream()

onMounted(() => {
  loadWorkspaces()
  loadWorkstreams()
})

// Only one layout exists — no auth/AuthLayout needed. `meta.layout` is kept
// on routes for forward-compatibility with the reference repos' pattern.
const layout = computed(() => DefaultLayout)
</script>

<template>
  <component :is="layout">
    <Alert v-if="error" variant="destructive" role="alert" class="mb-4">
      <AlertCircle class="size-4" aria-hidden="true" />
      <AlertTitle>Couldn't load workspaces</AlertTitle>
      <AlertDescription>{{ error }}</AlertDescription>
    </Alert>
    <RouterView />
  </component>
  <Toaster />
  <ConfirmDialogHost />
</template>
