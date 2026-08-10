import axios from 'axios'
import type { SearchResponse, Job } from '@/types/job'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 60000,
})

export async function searchJobs(
  q: string,
  location: string = 'india',
  date_hours: number = 24
): Promise<SearchResponse> {
  const { data } = await api.get<SearchResponse>('/api/jobs/search/', {
    params: {
      q,
      location,
      date_hours,
      min_score: 0.0,
      page_size: 50,
    },
  })
  return data
}

export async function getJob(id: string): Promise<Job> {
  const { data } = await api.get<Job>(`/api/jobs/${id}/`)
  return data
}
