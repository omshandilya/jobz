'use client'

import React from 'react'
import { Sparkles, Settings, LogOut, User as UserIcon, CheckCircle2, AlertCircle } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'

export default function Navbar({ children }: { children?: React.ReactNode }) {
  const { user, openAuthModal, openSettingsModal, logout } = useAuth()

  return (
    <header className="sticky top-0 z-30 border-b border-white/70 bg-white/78 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center shadow-md shadow-blue-200/70">
            <Sparkles size={18} className="text-white" />
          </div>
          <span className="text-2xl font-black text-slate-900 tracking-tight">Jobz</span>
        </div>

        {children && <div className="flex-1 max-w-2xl">{children}</div>}

        <div className="flex items-center gap-3 shrink-0">
          {user ? (
            <div className="flex items-center gap-3">
              <button
                onClick={openSettingsModal}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition ${
                  user.gmail_connected
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100'
                    : 'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100'
                }`}
                title={user.gmail_connected ? `Connected as ${user.gmail_email}` : 'Gmail not connected'}
              >
                {user.gmail_connected ? (
                  <>
                    <CheckCircle2 size={13} /> Gmail Connected
                  </>
                ) : (
                  <>
                    <AlertCircle size={13} /> Connect Gmail
                  </>
                )}
              </button>

              <button
                onClick={openSettingsModal}
                className="p-2 text-slate-600 hover:text-blue-700 hover:bg-blue-50 rounded-xl transition"
                title="Settings & Email Template"
              >
                <Settings size={19} />
              </button>

              <div className="hidden sm:flex flex-col text-right">
                <span className="text-sm font-bold text-slate-800 leading-none">{user.name || 'User'}</span>
                <span className="text-xs text-slate-500 truncate max-w-[140px]">{user.email}</span>
              </div>

              <button
                onClick={logout}
                className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition"
                title="Log Out"
              >
                <LogOut size={18} />
              </button>
            </div>
          ) : (
            <button
              onClick={openAuthModal}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl text-sm transition shadow-sm"
            >
              <UserIcon size={16} /> Sign In
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
