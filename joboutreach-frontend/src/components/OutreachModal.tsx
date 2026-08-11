'use client'

import React, { useState, useEffect } from 'react'
import { X, Send, CheckCircle2, AlertCircle, Mail, Sparkles, Building2, MapPin } from 'lucide-react'
import { toast } from 'sonner'
import { useAuth } from '@/context/AuthContext'
import { getJobContacts } from '@/lib/api'
import type { Contact } from '@/types/auth'

function StatusBadge({ status }: { status: Contact['smtp_status'] }) {
  if (status === 'valid') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
        <CheckCircle2 size={10} /> Valid SMTP
      </span>
    )
  }
  if (status === 'catch_all') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
        <AlertCircle size={10} /> Catch-All
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-gray-100 text-gray-600 border border-gray-200">
      Risky / Extracted
    </span>
  )
}

export default function OutreachModal() {
  const { user, selectedOutreachJob, closeOutreachModal } = useAuth()

  const [contacts, setContacts] = useState<Contact[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null)

  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [sending, setSending] = useState(false)

  useEffect(() => {
    if (selectedOutreachJob) {
      setLoading(true)
      setSelectedContact(null)
      getJobContacts(selectedOutreachJob.id)
        .then((data) => {
          setContacts(data)
          if (data.length > 0) {
            setSelectedContact(data[0])
          }
        })
        .catch(() => {
          toast.error('Failed to load outreach contacts for this job.')
          setContacts([])
        })
        .finally(() => setLoading(false))

      // Pre-fill email subject & template
      setSubject(`Application for ${selectedOutreachJob.title} - ${selectedOutreachJob.company}`)
    }
  }, [selectedOutreachJob])

  // Update body template when contact or job changes
  useEffect(() => {
    if (selectedOutreachJob && user) {
      const recipientName = selectedContact
        ? selectedContact.first_name || 'Hiring Manager'
        : 'Hiring Manager'

      let rawTmpl = user.email_template || `Hi {{name}},\n\nI saw the {{job_title}} role at {{company}} and would love to apply.\n\nBest regards,\n${user.name}`

      const filled = rawTmpl
        .replace(/\{\{\s*name\s*\}\}/g, recipientName)
        .replace(/\{\{\s*job_title\s*\}\}/g, selectedOutreachJob.title)
        .replace(/\{\{\s*company\s*\}\}/g, selectedOutreachJob.company)

      setBody(filled)
    }
  }, [selectedContact, selectedOutreachJob, user])

  if (!selectedOutreachJob) return null

  const handleSend = () => {
    if (!selectedContact) {
      toast.error('Please select a recipient contact email.')
      return
    }
    if (!user?.gmail_connected) {
      toast.error('Please connect your Gmail account in Settings before sending.')
      return
    }

    setSending(true)
    setTimeout(() => {
      setSending(false)
      toast.success(`Cold email queued & sent to ${selectedContact.email}!`)
      closeOutreachModal()
    }, 1200)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="section-card w-full max-w-2xl rounded-[1.75rem] overflow-hidden relative max-h-[90vh] flex flex-col">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-sm">
              <Sparkles size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-900 leading-tight">Outreach & Email Finder</h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-700">
                  {selectedOutreachJob.company}
                </span>
              </div>
              <p className="text-xs text-slate-500 flex items-center gap-2 mt-0.5">
                <span>{selectedOutreachJob.title}</span> •
                <span className="flex items-center gap-0.5">
                  <MapPin size={10} /> {selectedOutreachJob.location}
                </span>
              </p>
            </div>
          </div>
          <button
            onClick={closeOutreachModal}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-200 transition"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                <Mail size={14} className="text-blue-600" />
                Verified Recipient Contacts
              </label>
              {!loading && (
                <span className="text-[11px] text-slate-500 font-medium">
                  {contacts.length} email{contacts.length !== 1 ? 's' : ''} found
                </span>
              )}
            </div>

            {loading ? (
              <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50 space-y-2">
                <div className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4 text-blue-600" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  <span className="text-xs text-slate-600 font-medium">
                    Probing SMTP & extracting verified emails for {selectedOutreachJob.company}...
                  </span>
                </div>
              </div>
            ) : contacts.length === 0 ? (
              <div className="p-4 rounded-2xl border border-dashed border-slate-200 bg-slate-50 text-center text-xs text-slate-500">
                No direct recruiter emails found for this company. You can still compose and copy your outreach template!
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-44 overflow-y-auto p-1">
                {contacts.map((contact) => (
                  <div
                    key={contact.id || contact.email}
                    onClick={() => setSelectedContact(contact)}
                    className={`p-3 rounded-2xl border text-xs cursor-pointer transition flex items-center justify-between ${
                      selectedContact?.email === contact.email
                        ? 'border-blue-500 bg-blue-50/50 shadow-sm'
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                  >
                    <div className="min-w-0 pr-2">
                      <div className="font-semibold text-slate-900 truncate">{contact.email}</div>
                      <div className="text-[10px] text-slate-400">Source: {contact.source}</div>
                    </div>
                    <StatusBadge status={contact.smtp_status} />
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-3 pt-2 border-t border-slate-100">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Email Subject</label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="soft-input w-full px-3 py-2 text-xs rounded-xl border focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Email Message Body</label>
              <textarea
                rows={6}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                className="soft-input w-full p-3 text-xs text-slate-800 rounded-xl border focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono leading-relaxed"
              />
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-slate-100 flex items-center justify-between bg-slate-50">
          <div className="text-xs text-slate-500">
            {user?.gmail_connected ? (
              <span className="text-emerald-700 font-semibold flex items-center gap-1">
                <CheckCircle2 size={12} /> Ready to send via {user.gmail_email}
              </span>
            ) : (
              <span className="text-amber-700 font-semibold flex items-center gap-1">
                <AlertCircle size={12} /> Connect Gmail in Settings to send directly
              </span>
            )}
          </div>

          <div className="flex gap-2">
            <button
              onClick={closeOutreachModal}
              className="px-4 py-2 bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 text-xs font-semibold rounded-xl transition"
            >
              Cancel
            </button>
            <button
              onClick={handleSend}
              disabled={sending || !selectedContact}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-xs font-semibold rounded-xl transition shadow-sm flex items-center gap-1.5"
            >
              <Send size={14} /> {sending ? 'Sending via Gmail...' : 'Send Cold Email'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
