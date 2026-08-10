import axios from 'axios'
import type { SearchResponse, Job } from '@/types/job'
import type { User, AuthResponse, Contact } from '@/types/auth'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 120000,
})

// Attach Bearer token dynamically if available in localStorage
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// Jobs APIs
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

// Auth APIs
export async function registerUser(payload: { email: string; password: string; name: string }): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/api/auth/register/', payload)
  return data
}

export async function loginUser(payload: { email: string; password: string }): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/api/auth/login/', payload)
  return data
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>('/api/auth/me/')
  return data
}

export async function connectGmail(): Promise<{ auth_url: string }> {
  const { data } = await api.get<{ auth_url: string }>('/api/auth/gmail/connect/')
  return data
}

export async function updateEmailTemplate(email_template: string): Promise<User> {
  const { data } = await api.put<User>('/api/auth/template/', { email_template })
  return data
}

// Outreach APIs
export async function getJobContacts(jobId: string): Promise<Contact[]> {
  const { data } = await api.get<Contact[]>(`/api/outreach/contacts/${jobId}/`)
  return data
}
