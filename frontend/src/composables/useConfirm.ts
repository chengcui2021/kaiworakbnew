import { ref } from 'vue'

export interface ConfirmOptions {
  title: string
  description: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'default' | 'destructive'
  /** If set, the confirm action stays disabled until the user types this exact text. */
  requireText?: string
}

const isOpen = ref(false)
const options = ref<ConfirmOptions>({ title: '', description: '' })
let resolver: ((value: boolean) => void) | null = null

function settle(value: boolean) {
  isOpen.value = false
  resolver?.(value)
  resolver = null
}

/**
 * Promise-based confirm dialog — a drop-in replacement for the browser's
 * native `confirm()` that renders as the app's own shadcn AlertDialog
 * instead. Single shared dialog instance (mounted once via
 * `ConfirmDialogHost.vue` in App.vue); `confirm()` can be called from
 * anywhere, including per-row handlers in a list.
 */
export function useConfirm() {
  function confirm(opts: ConfirmOptions): Promise<boolean> {
    options.value = opts
    isOpen.value = true
    return new Promise((resolve) => {
      resolver = resolve
    })
  }

  return { confirm }
}

/** Internal — used only by ConfirmDialogHost.vue. */
export function useConfirmDialogState() {
  return { isOpen, options, settle }
}
