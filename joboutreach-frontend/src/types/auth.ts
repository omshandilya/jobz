export interface User {
  id: string
  email: string
  name: string
  gmail_connected: boolean
  gmail_email: string
  email_template: string
}

export interface AuthResponse {
  access: string
  refresh: string
  user: User
}

export interface Contact {
  id: string
  email: string
  first_name: string
  last_name: string
  title: string
  department: string
  source: 'jd_extract' | 'hunter' | 'smtp_pattern' | 'manual'
  smtp_status: 'valid' | 'risky' | 'catch_all' | 'not_found' | 'unverified'
  confidence_score: number
}
