// Render Markdown to sanitized HTML for display.
import DOMPurify from 'dompurify'
import { marked } from 'marked'

marked.setOptions({
  gfm: true,
  breaks: true,
})

function escapeHtml(text: string): string {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

// Fenced ```mermaid blocks are emitted as a placeholder element instead of a
// normal <pre><code> block. mermaidRender.ts finds these after sanitization
// and replaces them with a rendered SVG diagram. The source is stored
// URI-encoded in a data attribute (not as element text) so it can carry
// mermaid syntax like `<`, `>`, and quotes through DOMPurify unscathed.
marked.use({
  renderer: {
    code({ text, lang }) {
      const language = (lang ?? '').trim().split(/\s+/)[0]
      if (language !== 'mermaid') {
        return false
      }
      return `<pre class="mermaid" data-mermaid-src="${encodeURIComponent(text)}">${escapeHtml(text)}</pre>`
    },
  },
})

export function renderMarkdown(source: string | null | undefined): string {
  if (!source || !source.trim()) {
    return ''
  }
  const raw = marked.parse(source, { async: false }) as string
  return DOMPurify.sanitize(raw)
}
