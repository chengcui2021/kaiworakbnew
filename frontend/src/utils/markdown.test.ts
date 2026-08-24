import { describe, expect, it } from 'vitest'
import { renderMarkdown } from './markdown'

describe('renderMarkdown', () => {
  it('renders standard Markdown to sanitized HTML', () => {
    expect(renderMarkdown('# Hello world')).toContain('<h1>Hello world</h1>')
  })

  it('returns an empty string for empty/blank/nullish input', () => {
    expect(renderMarkdown('')).toBe('')
    expect(renderMarkdown('   ')).toBe('')
    expect(renderMarkdown(null)).toBe('')
    expect(renderMarkdown(undefined)).toBe('')
  })

  it('leaves non-mermaid fenced code blocks untouched', () => {
    const html = renderMarkdown('```js\nconst x = 1;\n```')
    expect(html).toContain('<pre><code class="language-js">')
    expect(html).not.toContain('data-mermaid-src')
  })

  it('emits a data-mermaid-src placeholder for fenced mermaid blocks', () => {
    const source = 'graph TD;\n  A-->B;'
    const html = renderMarkdown('```mermaid\n' + source + '\n```')

    expect(html).toContain('class="mermaid"')
    const match = html.match(/data-mermaid-src="([^"]*)"/)
    expect(match).not.toBeNull()
    expect(decodeURIComponent(match![1])).toBe(source)
  })

  it('sanitizes a mermaid block containing script/event-handler payloads with no unescaped breakout characters', () => {
    const payload = 'graph TD;\n  A["<script>alert(1)</script>"] --> B["x" onerror=alert(2)];'
    const html = renderMarkdown('```mermaid\n' + payload + '\n```')

    const match = html.match(/data-mermaid-src="([^"]*)"/)
    expect(match).not.toBeNull()
    // The attribute value itself must contain none of these raw characters -
    // encodeURIComponent already guarantees this, but assert it directly
    // since it's the property the mermaid-rendering pipeline relies on.
    expect(match![1]).not.toMatch(/[<>"]/)
    expect(decodeURIComponent(match![1])).toBe(payload)

    // The element's visible text content is HTML-escaped, not raw.
    expect(html).not.toContain('<script>alert(1)</script>')
    expect(html).toContain('&lt;script&gt;')
  })
})
