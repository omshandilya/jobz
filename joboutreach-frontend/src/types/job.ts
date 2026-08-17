export interface Job {
  id: string
  title: string
  company: string
  company_domain: string
  location: string
  experience_required: string
  source: 'naukri' | 'internshala' | 'indeed' | 'instahyre' | 'linkedin'
  source_url: string
  relevancy_score: number
  skills_extracted: string[]
  posted_at: string
  jd_preview: string
  is_active: boolean
}

export interface SearchResponse {
  count: number
  page: number
  total_pages: number
  scraping_active: boolean
  results: Job[]
}

export type SortMode = 'relevant' | 'recent'
export type SourceFilter = 'all' | 'naukri' | 'internshala' | 'indeed' | 'instahyre' | 'linkedin'
