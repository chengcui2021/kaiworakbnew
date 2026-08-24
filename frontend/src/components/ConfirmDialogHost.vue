<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useConfirmDialogState } from '@/composables/useConfirm'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const { isOpen, options, settle } = useConfirmDialogState()

const typedText = ref('')
// AlertDialogAction/Cancel close the dialog themselves on click (Reka UI's
// built-in behavior), which fires `onOpenChange(false)` *before* a normal
// `@click` listener attached from here would run — so a plain
// `@click="settle(true)"` on Action loses the race to onOpenChange's
// unconditional `settle(false)`. Recording intent in the capture phase
// (which always runs before the same element's bubble-phase internal
// handler) and letting onOpenChange be the single place that calls
// `settle()` avoids the race entirely.
const pendingResult = ref(false)

// Reset the typed-confirmation input each time a new confirm() is requested.
watch(isOpen, (open) => {
  if (open) typedText.value = ''
})

const confirmDisabled = computed(() => {
  const required = options.value.requireText
  return !!required && typedText.value !== required
})

function onOpenChange(open: boolean) {
  if (!open) {
    settle(pendingResult.value)
    pendingResult.value = false
  }
}
</script>

<template>
  <AlertDialog :open="isOpen" @update:open="onOpenChange">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>{{ options.title }}</AlertDialogTitle>
        <AlertDialogDescription>{{ options.description }}</AlertDialogDescription>
      </AlertDialogHeader>

      <div v-if="options.requireText" class="grid gap-2">
        <Label for="confirm-type-text">
          Type <strong>{{ options.requireText }}</strong> to confirm
        </Label>
        <Input id="confirm-type-text" v-model="typedText" autocomplete="off" />
      </div>

      <AlertDialogFooter>
        <AlertDialogCancel @click.capture="pendingResult = false">
          {{ options.cancelLabel || 'Cancel' }}
        </AlertDialogCancel>
        <AlertDialogAction
          :disabled="confirmDisabled"
          :class="
            options.variant === 'destructive'
              ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90'
              : undefined
          "
          @click.capture="pendingResult = true"
        >
          {{ options.confirmLabel || 'Confirm' }}
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
