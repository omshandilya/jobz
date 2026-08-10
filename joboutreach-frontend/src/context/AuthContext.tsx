'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'
import type { User } from '@/types/auth'
import type { Job } from '@/types/job'
import { getMe } from '@/lib/api'

interface AuthContextType {
  user: User | null
  loading: boolean
  isAuthModalOpen: boolean
  isSettingsModalOpen: boolean
  selectedOutreachJob: Job | null
  login: (access: string, refresh: string, user: User) => void
  logout: () => void
  setUser: React.Dispatch<React.SetStateAction<User | null>>
  openAuthModal: () => void
  closeAuthModal: () => void
  openSettingsModal: () => void
  closeSettingsModal: () => void
  openOutreachModal: (job: Job) => void
  closeOutreachModal: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false)
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false)
  const [selectedOutreachJob, setSelectedOutreachJob] = useState<Job | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      getMe()
        .then((userData) => setUser(userData))
        .catch(() => {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = (access: string, refresh: string, userData: User) => {
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    setUser(userData)
    setIsAuthModalOpen(false)
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
  }

  const openAuthModal = () => setIsAuthModalOpen(true)
  const closeAuthModal = () => setIsAuthModalOpen(false)

  const openSettingsModal = () => setIsSettingsModalOpen(true)
  const closeSettingsModal = () => setIsSettingsModalOpen(false)

  const openOutreachModal = (job: Job) => {
    if (!user) {
      setIsAuthModalOpen(true)
    } else {
      setSelectedOutreachJob(job)
    }
  }
  const closeOutreachModal = () => setSelectedOutreachJob(null)

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthModalOpen,
        isSettingsModalOpen,
        selectedOutreachJob,
        login,
        logout,
        setUser,
        openAuthModal,
        closeAuthModal,
        openSettingsModal,
        closeSettingsModal,
        openOutreachModal,
        closeOutreachModal,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
