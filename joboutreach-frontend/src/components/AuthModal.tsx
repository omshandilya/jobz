'use client'

import React, { useState } from 'react'
import { X, Lock, Mail, User, Sparkles } from 'lucide-react'
import { toast } from 'sonner'
import { useAuth } from '@/context/AuthContext'
import { loginUser, registerUser } from '@/lib/api'

export default function AuthModal() {
  const { isAuthModalOpen, closeAuthModal, login } = useAuth()
  const [tab, setTab] = useState<'login' | 'register'>('login')

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (!isAuthModalOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)

    try {
      if (tab === 'login') {
        const res = await loginUser({ email, password })
        login(res.access, res.refresh, res.user)
        toast.success(`Welcome back, ${res.user.name || res.user.email}!`)
      } else {
        const res = await registerUser({ email, password, name })
        login(res.access, res.refresh, res.user)
        toast.success('Account created successfully!')
      }
    } catch (err: any) {
      const errMsg = err?.response?.data?.error || 'Authentication failed. Please check details.'
      toast.error(errMsg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="section-card w-full max-w-md rounded-[1.75rem] overflow-hidden relative">
        <button
          onClick={closeAuthModal}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition"
        >
          <X size={18} />
        </button>

        <div className="p-6 pb-4 border-b border-slate-100 text-center">
          <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-3">
            <Sparkles size={24} />
          </div>
          <h2 className="text-xl font-bold text-slate-900">
            {tab === 'login' ? 'Sign in to Jobz' : 'Create your account'}
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            {tab === 'login'
              ? 'Access candidate outreach and Gmail integration'
              : 'Start reaching out to recruiters instantly'}
          </p>

          <div className="flex bg-slate-100 p-1 rounded-xl mt-4">
            <button
              onClick={() => setTab('login')}
              className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition ${
                tab === 'login' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => setTab('register')}
              className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition ${
                tab === 'register' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              Register
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {tab === 'register' && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name</label>
              <div className="relative">
                <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="John Doe"
                  className="soft-input w-full pl-9 pr-3 py-2.5 text-sm rounded-xl border focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address</label>
            <div className="relative">
              <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="soft-input w-full pl-9 pr-3 py-2.5 text-sm rounded-xl border focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Password</label>
            <div className="relative">
              <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="soft-input w-full pl-9 pr-3 py-2.5 text-sm rounded-xl border focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold rounded-xl text-sm transition shadow-sm"
          >
            {submitting ? 'Please wait...' : tab === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  )
}
