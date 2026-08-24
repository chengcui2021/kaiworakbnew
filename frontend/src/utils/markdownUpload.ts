// Client-side validation and reading for Markdown file uploads.

/** Matches API `content` max length (POST /entries). */
export const MAX_MARKDOWN_CHARS = 100_000

/** Reject obviously huge files before reading into memory. */
export const MAX_MARKDOWN_FILE_BYTES = 512_000

const MARKDOWN_EXTENSIONS = new Set(['.md', '.markdown', '.mdown', '.mkd'])

export function isMarkdownFilename(name: string): boolean {
  const lower = String(name || '').toLowerCase()
  const dot = lower.lastIndexOf('.')
  if (dot < 0) return false
  return MARKDOWN_EXTENSIONS.has(lower.slice(dot))
}

/** Returns an error message, or null if the file is valid. */
export function validateMarkdownFile(file: File | null | undefined): string | null {
  if (!file) {
    return 'No file selected.'
  }
  if (!isMarkdownFilename(file.name)) {
    return 'Only .md / .markdown files are supported.'
  }
  if (file.size === 0) {
    return 'The file is empty.'
  }
  if (file.size > MAX_MARKDOWN_FILE_BYTES) {
    return `File is too large (max ${Math.round(MAX_MARKDOWN_FILE_BYTES / 1024)} KB).`
  }
  return null
}

// --- Transform-specific validation (accepts .md + .pdf) ---

const PDF_EXTENSIONS = new Set(['.pdf'])
const TRANSFORM_EXTENSIONS = new Set([...MARKDOWN_EXTENSIONS, ...PDF_EXTENSIONS])

export const MAX_PDF_FILE_BYTES = 5_000_000 // 5 MB — matches backend limit

export function isPdfFilename(name: string): boolean {
  const lower = String(name || '').toLowerCase()
  const dot = lower.lastIndexOf('.')
  if (dot < 0) return false
  return PDF_EXTENSIONS.has(lower.slice(dot))
}

export function validateTransformFile(file: File | null | undefined): string | null {
  if (!file) return 'No file selected.'
  const lower = String(file.name || '').toLowerCase()
  const dot = lower.lastIndexOf('.')
  if (dot < 0 || !TRANSFORM_EXTENSIONS.has(lower.slice(dot))) {
    return 'Only .md and .pdf files are supported.'
  }
  if (file.size === 0) return 'The file is empty.'
  if (isPdfFilename(file.name)) {
    if (file.size > MAX_PDF_FILE_BYTES) {
      return `PDF is too large (max ${Math.round(MAX_PDF_FILE_BYTES / 1_000_000)} MB).`
    }
  } else {
    if (file.size > MAX_MARKDOWN_FILE_BYTES) {
      return `File is too large (max ${Math.round(MAX_MARKDOWN_FILE_BYTES / 1024)} KB).`
    }
  }
  return null
}

export function readMarkdownFile(file: File): Promise<string> {
  const validationError = validateMarkdownFile(file)
  if (validationError) {
    return Promise.reject(new Error(validationError))
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const text = typeof reader.result === 'string' ? reader.result : ''
      const trimmed = text.trim()
      if (!trimmed) {
        reject(new Error('The file has no Markdown content.'))
        return
      }
      if (trimmed.length > MAX_MARKDOWN_CHARS) {
        reject(new Error(`Content exceeds ${MAX_MARKDOWN_CHARS.toLocaleString()} character limit.`))
        return
      }
      resolve(text)
    }
    reader.onerror = () => {
      reject(new Error('Could not read the file. Try again.'))
    }
    reader.readAsText(file)
  })
}
