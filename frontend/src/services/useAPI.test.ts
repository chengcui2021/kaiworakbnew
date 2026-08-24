import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useApi } from './useAPI'

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

function createFetchResponse(data: unknown, ok = true, status = 200, statusText = 'OK') {
  return {
    ok,
    status,
    statusText,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  }
}

/** Same as useAPI: relative paths use `${VITE_API_BASE_URL}${path}` */
function resolvedUrl(path: string) {
  const base = import.meta.env.VITE_API_BASE_URL || ''
  return `${base}${path}`
}

describe('useApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('returns correct initial values', () => {
      const { responseData, loading, error } = useApi()
      expect(responseData.value).toBeNull()
      expect(loading.value).toBe(false)
      expect(error.value).toBeNull()
    })
  })

  describe('GET requests', () => {
    it('makes a successful GET request', async () => {
      const mockData = { id: 1, name: 'Test' }
      mockFetch.mockResolvedValueOnce(createFetchResponse(mockData))

      const { makeRequest, responseData, loading } = useApi<typeof mockData>()
      const result = await makeRequest.get('/api/test')

      expect(mockFetch).toHaveBeenCalledWith(
        resolvedUrl('/api/test'),
        expect.objectContaining({
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        })
      )
      expect(result).toEqual(mockData)
      expect(responseData.value).toEqual(mockData)
      expect(loading.value).toBe(false)
    })
  })

  describe('POST requests', () => {
    it('sends body as JSON', async () => {
      const body = { name: 'New Item' }
      mockFetch.mockResolvedValueOnce(createFetchResponse({ id: 1 }))

      const { makeRequest } = useApi()
      await makeRequest.post('/api/items', { body })

      expect(mockFetch).toHaveBeenCalledWith(
        resolvedUrl('/api/items'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(body),
        })
      )
    })
  })

  describe('all HTTP methods', () => {
    it.each(['get', 'post', 'put', 'delete', 'patch'] as const)(
      'supports %s method',
      async (method) => {
        mockFetch.mockResolvedValueOnce(createFetchResponse({}))

        const { makeRequest } = useApi()
        await makeRequest[method]('/api/test')

        expect(mockFetch).toHaveBeenCalledWith(
          resolvedUrl('/api/test'),
          expect.objectContaining({ method: method.toUpperCase() })
        )
      }
    )
  })

  describe('custom headers', () => {
    it('merges custom headers with defaults', async () => {
      mockFetch.mockResolvedValueOnce(createFetchResponse({}))

      const { makeRequest } = useApi()
      await makeRequest.get('/api/test', {
        headers: { Authorization: 'Bearer token123' },
      })

      expect(mockFetch).toHaveBeenCalledWith(
        resolvedUrl('/api/test'),
        expect.objectContaining({
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer token123',
          },
        })
      )
    })
  })

  describe('FormData handling', () => {
    it('removes Content-Type header for FormData body', async () => {
      const formData = new FormData()
      formData.append('file', 'test')
      mockFetch.mockResolvedValueOnce(createFetchResponse({}))

      const { makeRequest } = useApi()
      await makeRequest.post('/api/upload', { body: formData })

      const callHeaders = mockFetch.mock.calls[0][1].headers
      expect(callHeaders['Content-Type']).toBeUndefined()
      expect(mockFetch.mock.calls[0][1].body).toBe(formData)
    })
  })

  describe('mock mode', () => {
    it('returns mock data without calling fetch', async () => {
      const mockData = { id: 99, name: 'Mocked' }

      const { makeRequest, responseData } = useApi()
      const result = await makeRequest.get('/api/test', {
        mocked: true,
        mockResponse: mockData,
      })

      expect(mockFetch).not.toHaveBeenCalled()
      expect(result).toEqual(mockData)
      expect(responseData.value).toEqual(mockData)
    })

    it('applies transformResponse in mock mode', async () => {
      const { makeRequest, responseData } = useApi()
      const result = await makeRequest.get<{ count: number }>('/api/test', {
        mocked: true,
        mockResponse: { count: 5 },
        transformResponse: (data) => ({ count: data.count * 2 }),
      })

      expect(result).toEqual({ count: 10 })
      expect(responseData.value).toEqual({ count: 10 })
    })
  })

  describe('transformResponse', () => {
    it('transforms the response data', async () => {
      mockFetch.mockResolvedValueOnce(createFetchResponse({ items: [1, 2, 3] }))

      const { makeRequest, responseData } = useApi()
      const result = await makeRequest.get<{ items: number[] }>('/api/test', {
        transformResponse: (data) => ({ items: data.items.map((n) => n * 10) }),
      })

      expect(result).toEqual({ items: [10, 20, 30] })
      expect(responseData.value).toEqual({ items: [10, 20, 30] })
    })
  })

  describe('lifecycle hooks', () => {
    it('calls onBefore before the request', async () => {
      const onBefore = vi.fn()
      mockFetch.mockResolvedValueOnce(createFetchResponse({}))

      const { makeRequest } = useApi()
      await makeRequest.get('/api/test', { onBefore })

      expect(onBefore).toHaveBeenCalledOnce()
    })

    it('calls onSuccess with the response data', async () => {
      const onSuccess = vi.fn()
      const mockData = { result: 'ok' }
      mockFetch.mockResolvedValueOnce(createFetchResponse(mockData))

      const { makeRequest } = useApi()
      await makeRequest.get('/api/test', { onSuccess })

      expect(onSuccess).toHaveBeenCalledWith(mockData)
    })

    it('calls onError when request fails', async () => {
      const onError = vi.fn()
      mockFetch.mockResolvedValueOnce(
        createFetchResponse({ detail: 'Not found' }, false, 404, 'Not Found')
      )

      const { makeRequest } = useApi()

      await expect(makeRequest.get('/api/test', { onError })).rejects.toThrow()
      expect(onError).toHaveBeenCalledWith(expect.any(Error))
    })

    it('calls onFinally after success', async () => {
      const onFinally = vi.fn()
      mockFetch.mockResolvedValueOnce(createFetchResponse({}))

      const { makeRequest } = useApi()
      await makeRequest.get('/api/test', { onFinally })

      expect(onFinally).toHaveBeenCalledOnce()
    })

    it('calls onFinally after error', async () => {
      const onFinally = vi.fn()
      mockFetch.mockResolvedValueOnce(createFetchResponse({}, false, 500, 'Server Error'))

      const { makeRequest } = useApi()
      await makeRequest.get('/api/test', { onFinally }).catch(() => {})

      expect(onFinally).toHaveBeenCalledOnce()
    })

    it('calls onSuccess in mock mode', async () => {
      const onSuccess = vi.fn()
      const mockData = { mocked: true }

      const { makeRequest } = useApi()
      await makeRequest.get('/api/test', {
        mocked: true,
        mockResponse: mockData,
        onSuccess,
      })

      expect(onSuccess).toHaveBeenCalledWith(mockData)
    })
  })

  describe('error handling', () => {
    it('sets error state on failed response', async () => {
      mockFetch.mockResolvedValueOnce(
        createFetchResponse({ detail: 'Resource not found' }, false, 404, 'Not Found')
      )

      const { makeRequest, error } = useApi()
      await makeRequest.get('/api/test').catch(() => {})

      expect(error.value).toBeTruthy()
    })

    it('uses the detail message from the response body', async () => {
      mockFetch.mockResolvedValueOnce(
        createFetchResponse({ detail: 'Resource not found' }, false, 404, 'Not Found')
      )

      const { makeRequest, error } = useApi()
      await makeRequest.get('/api/test').catch(() => {})

      expect(error.value).toBe('Resource not found')
    })

    it('uses customErrorMessage when provided', async () => {
      mockFetch.mockResolvedValueOnce(createFetchResponse({}, false, 500, 'Server Error'))

      const { makeRequest, error } = useApi()
      await makeRequest.get('/api/test', { customErrorMessage: 'Something broke' }).catch(() => {})

      expect(error.value).toBe('Something broke')
    })

    it('uses errorMap for status-specific messages', async () => {
      mockFetch.mockResolvedValueOnce(createFetchResponse({}, false, 404, 'Not Found'))

      const { makeRequest, error } = useApi()
      await makeRequest
        .get('/api/test', {
          errorMap: { 404: 'Custom not found message' },
        })
        .catch(() => {})

      expect(error.value).toBe('Custom not found message')
    })

    it('falls back to statusText when no detail or errorMap entry exists', async () => {
      mockFetch.mockResolvedValueOnce(createFetchResponse({}, false, 418, "I'm a teapot"))

      const { makeRequest, error } = useApi()
      await makeRequest.get('/api/test').catch(() => {})

      expect(error.value).toBe("Request failed: I'm a teapot")
    })

    it('handles network errors (fetch throws)', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'))

      const { makeRequest, error } = useApi()
      await makeRequest.get('/api/test').catch(() => {})

      expect(error.value).toBe('Network error: Unable to connect to the server')
    })

    it('throws error on failed response', async () => {
      mockFetch.mockResolvedValueOnce(createFetchResponse({}, false, 500, 'Server Error'))

      const { makeRequest } = useApi()
      await expect(makeRequest.get('/api/test')).rejects.toThrow()
    })
  })

  describe('clearErrorMessage', () => {
    it('clears the error state', async () => {
      mockFetch.mockResolvedValueOnce(createFetchResponse({}, false, 500, 'Server Error'))

      const { makeRequest, error, clearErrorMessage } = useApi()
      await makeRequest.get('/api/test').catch(() => {})

      expect(error.value).toBeTruthy()
      clearErrorMessage()
      expect(error.value).toBeNull()
    })
  })

  describe('loading state', () => {
    it('sets loading to false after successful request', async () => {
      mockFetch.mockResolvedValueOnce(createFetchResponse({}))

      const { makeRequest, loading } = useApi()
      await makeRequest.get('/api/test')

      expect(loading.value).toBe(false)
    })

    it('sets loading to false after failed request', async () => {
      mockFetch.mockResolvedValueOnce(createFetchResponse({}, false, 500, 'Server Error'))

      const { makeRequest, loading } = useApi()
      await makeRequest.get('/api/test').catch(() => {})

      expect(loading.value).toBe(false)
    })
  })
})
