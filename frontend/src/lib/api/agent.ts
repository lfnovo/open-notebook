import { getApiUrl } from '../config'

export interface PaperResult {
  title: string
  year?: number
  venue: string
  citations?: number
  pdf_url: string
  openalex_id?: string
  abstract_index: boolean
}

export interface SearchPapersResponse {
  count: number
  results: PaperResult[]
}

export interface IngestPaperRequest {
  pdf_url: string
  notebook_id: string
  title?: string
}

export interface IngestPaperResponse {
  success: boolean
  message: string
  source_id?: string
  command_id?: string
}

export async function searchAcmPapers(query: string, limit: number = 5): Promise<SearchPapersResponse> {
  const apiUrl = await getApiUrl()
  const response = await fetch(`${apiUrl}/api/agent/acm/search?query=${encodeURIComponent(query)}&limit=${limit}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to search papers: ${response.statusText}`)
  }

  return response.json()
}

export async function ingestAcmPaper(data: IngestPaperRequest): Promise<IngestPaperResponse> {
  const apiUrl = await getApiUrl()
  const response = await fetch(`${apiUrl}/api/agent/acm/ingest`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    throw new Error(`Failed to ingest paper: ${response.statusText}`)
  }

  return response.json()
}
