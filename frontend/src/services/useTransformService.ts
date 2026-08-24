import { useApi } from './useAPI'

export interface TransformResponse {
  content: string
}

export function useTransformService() {
  function transformText(
    documentText: string,
    templateContent: string
  ): Promise<TransformResponse> {
    const formData = new FormData()
    formData.append('document_text', documentText)
    formData.append('template_content', templateContent)

    return useApi<TransformResponse>().makeRequest.post('/api/transform', {
      body: formData,
    })
  }

  function transformPdf(file: File, templateContent: string): Promise<TransformResponse> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('template_content', templateContent)

    return useApi<TransformResponse>().makeRequest.post('/api/transform', {
      body: formData,
    })
  }

  return { transformText, transformPdf }
}
