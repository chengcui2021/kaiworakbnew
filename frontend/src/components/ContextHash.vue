<script setup lang="ts">
import { ref } from 'vue'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

const props = defineProps<{ hash: string; truncate?: boolean }>()

const copied = ref(false)

// Show the algorithm prefix plus a short prefix of the digest when truncating.
function shortHash(hash: string): string {
  const [algo, digest] = hash.split(':')
  if (!digest) return hash
  return `${algo}:${digest.slice(0, 12)}…`
}

async function copy() {
  try {
    await navigator.clipboard.writeText(props.hash)
  } catch {
    // Clipboard may be unavailable (e.g. insecure context); fall back silently.
  }
  copied.value = true
  window.setTimeout(() => (copied.value = false), 1500)
}
</script>

<template>
  <span class="inline-flex items-center gap-2" data-test="context-hash">
    <Tooltip>
      <TooltipTrigger as-child>
        <code class="rounded bg-muted px-1.5 py-0.5 text-xs">{{
          truncate ? shortHash(hash) : hash
        }}</code>
      </TooltipTrigger>
      <TooltipContent>
        SHA256 integrity hash — verifies the bundled content has not been altered<br />
        {{ hash }}
      </TooltipContent>
    </Tooltip>
    <Button variant="outline" size="sm" aria-live="polite" data-test="copy-hash" @click="copy">
      {{ copied ? 'Copied!' : 'Copy' }}
    </Button>
  </span>
</template>
