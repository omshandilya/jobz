'use client'

import React from 'react'
import { Sparkles, Settings, LogOut, User as UserIcon, CheckCircle2, AlertCircle } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'

export default function Navbar({ children }: { children?: React.ReactNode }) {
  const { user, openAuthModal, openSettingsModal, logout } = useAuth()

  return (
    <header className="bg-white border-b border-gray-100 sticky top-0 z-30 shadow-sm">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3.5 flex items-center justify-between gap-4">
        {/* Brand Logo */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center shadow-sm">
            <Sparkles size={18} className="text-white" />
          </div>
          <span className="text-2xl font-black text-gray-900 tracking-tight">Jobz</span>
        </div>

        {/* Children (e.g. SearchBar in header) */}
        {children && <div className="flex-1 max-w-2xl">{children}</div>}

        {/* Auth / Profile Actions */}
        <div className="flex items-center gap-3 shrink-0">
          {user ? (
            <div className="flex items-center gap-3">
              {/* Gmail Status Pill */}
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

              {/* Settings button */}
              <button
                onClick={openSettingsModal}
                className="p-2 text-gray-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition"
                title="Settings & Email Template"
              >
                <Settings size={19} />
              </button>

              {/* User info */}
              <div className="hidden sm:flex flex-col text-right">
                <span className="text-sm font-bold text-gray-800 leading-none">{user.name || 'User'}</span>
                <span className="text-xs text-gray-400 truncate max-w-[140px]">{user.email}</span>
              </div>

              {/* Logout button */}
              <button
                onClick={logout}
                className="p-2 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition"
                title="Log Out"
              >
                <LogOut size={18} />
              </button>
            </div>
          ) : (
            <button
              onClick={openAuthModal}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl text-sm transition shadow-sm"
            >
              <UserIcon size={16} /> Sign In
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
