'use client'

import React, { useState } from 'react'
import { X, Mail, CheckCircle2, AlertCircle, Save, Sparkles, ExternalLink } from 'lucide-react'
import { toast } from 'sonner'
import { useAuth } from '@/context/AuthContext'
import { connectGmail, updateEmailTemplate } from '@/lib/api'

const DEFAULT_TEMPLATE = `Hi {{name}},

I saw the {{job_title}} role at {{company}} and would love to apply. My background in software development aligns well with your team's requirements.

I have attached my resume for your review. Would you be open to a quick call this week?

Best regards,`

export default function SettingsModal() {
  const { user, isSettingsModalOpen, closeSettingsModal, setUser } = useAuth()
  const [template, setTemplate] = useState(user?.email_template || DEFAULT_TEMPLATE)
  const [saving, setSaving] = useState(false)
  const [connecting, setConnecting] = useState(false)

  if (!isSettingsModalOpen || !user) return null

  const handleConnectGmail = async () => {
    setConnecting(true)
    try {
      const res = await connectGmail()
      if (res.auth_url) {
        window.location.href = res.auth_url
      }
    } catch {
      toast.error('Failed to generate Gmail OAuth URL.')
      setConnecting(false)
    }
  }

  const handleSaveTemplate = async () => {
    setSaving(true)
    try {
      const updatedUser = await updateEmailTemplate(template)
      setUser(updatedUser)
      toast.success('Cold email template saved successfully!')
    } catch {
      toast.error('Failed to save email template.')
    } finally {
      setSaving(false)
    }
  }

  const appendTag = (tag: string) => {
    setTemplate((prev) => prev + ` ${tag} `)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="section-card w-full max-w-xl rounded-[1.75rem] overflow-hidden relative max-h-[90vh] flex flex-col">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <Sparkles size={18} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900 leading-tight">Settings & Outreach Config</h2>
              <p className="text-xs text-slate-500">Configure Gmail OAuth & default outreach template</p>
            </div>
          </div>
          <button
            onClick={closeSettingsModal}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-white border border-slate-200 flex items-center justify-center text-red-500 shadow-sm shrink-0">
                <Mail size={20} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-900">Gmail Integration</h3>
                  {user.gmail_connected ? (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                      <CheckCircle2 size={10} /> Connected
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
                      <AlertCircle size={10} /> Not Connected
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  {user.gmail_connected
                    ? `Connected email: ${user.gmail_email}`
                    : 'Authorize Gmail to send cold outreach emails directly from your account.'}
                </p>
              </div>
            </div>

            <button
              onClick={handleConnectGmail}
              disabled={connecting}
              className="px-4 py-2 bg-white border border-slate-300 hover:border-blue-400 hover:text-blue-700 text-slate-700 text-xs font-semibold rounded-lg transition shadow-sm shrink-0 flex items-center gap-1.5"
            >
              {connecting ? 'Connecting...' : user.gmail_connected ? 'Reconnect' : 'Connect Gmail'}
              <ExternalLink size={12} />
            </button>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-900">Cold Email Template</label>
              <div className="flex items-center gap-1 text-[11px] text-slate-500 flex-wrap justify-end">
                Insert tags:
                <button
                  type="button"
                  onClick={() => appendTag('{{name}}')}
                  className="px-1.5 py-0.5 rounded bg-slate-100 hover:bg-blue-50 hover:text-blue-700 font-mono text-[10px] text-slate-700"
                >
                  {"{{name}}"}
                </button>
                <button
                  type="button"
                  onClick={() => appendTag('{{job_title}}')}
                  className="px-1.5 py-0.5 rounded bg-slate-100 hover:bg-blue-50 hover:text-blue-700 font-mono text-[10px] text-slate-700"
                >
                  {"{{job_title}}"}
                </button>
                <button
                  type="button"
                  onClick={() => appendTag('{{company}}')}
                  className="px-1.5 py-0.5 rounded bg-slate-100 hover:bg-blue-50 hover:text-blue-700 font-mono text-[10px] text-slate-700"
                >
                  {"{{company}}"}
                </button>
              </div>
            </div>

            <textarea
              rows={7}
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              placeholder="Write your default outreach email template..."
              className="soft-input w-full p-3.5 text-xs text-slate-800 rounded-xl border focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono leading-relaxed bg-white"
            />
          </div>
        </div>

        <div className="p-4 border-t border-slate-100 flex justify-end gap-2 bg-slate-50">
          <button
            onClick={closeSettingsModal}
            className="px-4 py-2 bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 text-xs font-semibold rounded-xl transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSaveTemplate}
            disabled={saving}
            className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl transition shadow-sm flex items-center gap-1.5"
          >
            <Save size={14} /> {saving ? 'Saving...' : 'Save Template'}
          </button>
        </div>
      </div>
    </div>
  )
}
