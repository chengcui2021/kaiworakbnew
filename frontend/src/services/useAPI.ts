import { readonly, ref } from 'vue'

const apiUrl = import.meta.env.VITE_API_BASE_URL || ''

const defaultErrorMap: Record<number, string> = {
  0: 'Network error occurred',
  400: 'Bad request: The server could not understand the request',
  401: 'Unauthorized: Authentication is required',
  403: "Forbidden: You don't have permission to access this resource",
  404: 'Not found: The requested resource could not be found',
  500: 'Server error: Something went wrong on the server',
  502: 'Bad gateway: The server received an invalid response',
  503: 'Service unavailable: The server is temporarily unavailable',
  504: 'Gateway timeout: The server took too long to respond',
}

export interface ApiOptions<TResponse> {
  headers?: Record<string, string>
  body?: unknown
  mocked?: boolean
  delay?: number
  errorMap?: Record<number, string>
  customErrorMessage?: string
  mockResponse?: unknown
  transformResponse?: (data: TResponse) => unknown
  onBefore?: () => void
  onSuccess?: (data: TResponse) => TResponse | void
  onError?: (err: Error) => void
  onFinally?: () => void
}

async function parseErrorDetail(response: Response): Promise<string | null> {
  try {
    const text = await response.text()
    if (!text) return null
    const parsed = JSON.parse(text)
    return typeof parsed?.detail === 'string' ? parsed.detail : null
  } catch {
    return null
  }
}

/**
 * API composable for making HTTP requests.
 * Trimmed from the sibling repos' useAPI.ts: metamorphic-kb has no
 * authentication, so there's no 401-retry/token-refresh/cookie logic here.
 */
export function useApi<TResponse>() {
  const responseData = ref<TResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function makeRequest<T = TResponse>(
    url: string,
    method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
    opts: ApiOptions<T> = {}
  ): Promise<T> {
    const {
      body,
      headers = {},
      mocked = false,
      delay = 0,
      errorMap: customErrorMap,
      customErrorMessage,
      mockResponse,
      transformResponse,
      onBefore,
      onSuccess,
      onError,
      onFinally,
    } = opts

    const errorMap = customErrorMap ? { ...defaultErrorMap, ...customErrorMap } : defaultErrorMap

    function fail(message: string): never {
      error.value = message
      const err = new Error(message)
      onError?.(err)
      throw err
    }

    loading.value = true
    error.value = null

    try {
      onBefore?.()

      if (delay > 0) {
        await new Promise((resolve) => setTimeout(resolve, delay))
      }

      if (mocked) {
        const data = transformResponse ? transformResponse(mockResponse as T) : mockResponse
        responseData.value = data as unknown as TResponse
        onSuccess?.(data as T)
        return data as T
      }

      const isFormData = typeof FormData !== 'undefined' && body instanceof FormData
      const finalHeaders: Record<string, string> = isFormData
        ? { ...headers }
        : { 'Content-Type': 'application/json', ...headers }

      let response: Response
      try {
        response = await fetch(`${apiUrl}${url}`, {
          method,
          headers: finalHeaders,
          body: isFormData ? (body as FormData) : body ? JSON.stringify(body) : undefined,
        })
      } catch (fetchError) {
        const networkMessage =
          fetchError instanceof TypeError
            ? 'Network error: Unable to connect to the server'
            : errorMap[0] || 'Network error occurred while fetching data'
        return fail(customErrorMessage || networkMessage)
      }

      if (!response.ok) {
        const detail = await parseErrorDetail(response)
        return fail(
          customErrorMessage ||
            detail ||
            errorMap[response.status] ||
            `Request failed: ${response.statusText}`
        )
      }

      let jsonData: unknown
      try {
        jsonData = await response.json()
      } catch {
        jsonData = {}
      }
      const data = transformResponse ? transformResponse(jsonData as T) : jsonData
      responseData.value = data as unknown as TResponse
      onSuccess?.(data as T)
      return data as T
    } finally {
      loading.value = false
      onFinally?.()
    }
  }

  return {
    responseData: readonly(responseData),
    loading: readonly(loading),
    error: readonly(error),
    clearErrorMessage: () => {
      error.value = null
    },
    makeRequest: {
      get: <T = TResponse>(url: string, opts?: ApiOptions<T>) => makeRequest<T>(url, 'GET', opts),
      post: <T = TResponse>(url: string, opts?: ApiOptions<T>) => makeRequest<T>(url, 'POST', opts),
      put: <T = TResponse>(url: string, opts?: ApiOptions<T>) => makeRequest<T>(url, 'PUT', opts),
      patch: <T = TResponse>(url: string, opts?: ApiOptions<T>) =>
        makeRequest<T>(url, 'PATCH', opts),
      delete: <T = TResponse>(url: string, opts?: ApiOptions<T>) =>
        makeRequest<T>(url, 'DELETE', opts),
    },
  }
}
