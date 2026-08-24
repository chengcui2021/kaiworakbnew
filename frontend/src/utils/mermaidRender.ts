// Finds ```mermaid placeholders emitted by markdown.ts (`<pre class="mermaid"
// data-mermaid-src="...">`) inside a rendered preview container and replaces
// each with a rendered SVG diagram. Mermaid is dynamically imported so it
// only loads into the bundle where a preview actually contains a diagram.
import DOMPurify from 'dompurify'

let mermaidModulePromise: ReturnType<typeof loadMermaid> | undefined

async function loadMermaid() {
  const { default: mermaid } = await import('mermaid')
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: 'strict',
    // Mermaid's default label rendering wraps text in an HTML <span> inside
    // an SVG <foreignObject> — but DOMPurify's SVG sanitize profile (below)
    // treats foreignObject as unsafe and strips the tag *and its contents*,
    // silently deleting all node/edge text while leaving the shapes intact.
    // Forcing native SVG <text> labels keeps everything within DOMPurify's
    // allowed SVG element set.
    htmlLabels: false,
  })
  return mermaid
}

function getMermaid() {
  mermaidModulePromise ??= loadMermaid()
  return mermaidModulePromise
}

let diagramCounter = 0

function renderInlineError(node: HTMLElement, message: string): void {
  const errorEl = document.createElement('p')
  errorEl.className = 'text-sm text-destructive'
  errorEl.textContent = `Invalid Mermaid diagram: ${message}`
  node.replaceChildren(errorEl)
  node.removeAttribute('data-mermaid-src')
}

export async function renderMermaidDiagrams(container: HTMLElement): Promise<void> {
  const nodes = container.querySelectorAll<HTMLElement>('pre.mermaid[data-mermaid-src]')
  if (nodes.length === 0) {
    return
  }

  const mermaid = await getMermaid()

  await Promise.all(
    Array.from(nodes).map(async (node) => {
      const encodedSource = node.dataset.mermaidSrc
      if (!encodedSource) {
        return
      }
      const source = decodeURIComponent(encodedSource)
      diagramCounter += 1
      const id = `mermaid-diagram-${diagramCounter}`

      try {
        const { svg } = await mermaid.render(id, source)
        const sanitizedSvg = DOMPurify.sanitize(svg, {
          USE_PROFILES: { svg: true, svgFilters: true },
        })
        node.innerHTML = sanitizedSvg
        node.removeAttribute('data-mermaid-src')
        node.classList.add('mermaid-rendered')
      } catch (err) {
        renderInlineError(node, err instanceof Error ? err.message : 'could not render diagram')
      }
    })
  )
}
