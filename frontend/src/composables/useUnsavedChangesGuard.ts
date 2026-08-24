import { onBeforeUnmount, onMounted } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useConfirm } from './useConfirm'

/**
 * Warns before losing unsaved form edits, on both navigation paths:
 * - in-app route changes (Vue Router) — confirmed via the app's own dialog
 * - tab close / refresh / external navigation — browsers only allow their
 *   own generic native prompt here (no custom UI is possible), which is
 *   standard, expected behavior users already recognize.
 */
export function useUnsavedChangesGuard(isDirty: () => boolean) {
  const { confirm } = useConfirm()

  function onBeforeUnload(event: BeforeUnloadEvent) {
    if (!isDirty()) return
    event.preventDefault()
    event.returnValue = ''
  }

  onMounted(() => window.addEventListener('beforeunload', onBeforeUnload))
  onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload))

  onBeforeRouteLeave(async () => {
    if (!isDirty()) return true
    return confirm({
      title: 'Leave without saving?',
      description: 'You have unsaved changes that will be lost if you leave this page.',
      confirmLabel: 'Leave without saving',
      cancelLabel: 'Stay on this page',
      variant: 'destructive',
    })
  })
}
