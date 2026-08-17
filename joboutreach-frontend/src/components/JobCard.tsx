'use client'

import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { MapPin, Briefcase, ExternalLink, ChevronDown, ChevronUp, Send } from 'lucide-react'
import type { Job } from '@/types/job'
import { useAuth } from '@/context/AuthContext'

interface JobCardProps {
  job: Job
}

const SOURCE_CONFIG: Record<Job['source'], { label: string; color: string; bg: string }> = {
  naukri: { label: 'Naukri', color: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-200' },
  internshala: { label: 'Internshala', color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200' },
  indeed: { label: 'Indeed', color: 'text-indigo-700', bg: 'bg-indigo-50 border-indigo-200' },
  linkedin: { label: 'LinkedIn', color: 'text-sky-700', bg: 'bg-sky-50 border-sky-200' },
  instahyre: { label: 'Instahyre', color: 'text-purple-700', bg: 'bg-purple-50 border-purple-200' },
}

function RelevancyBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color =
    score >= 0.8
      ? 'from-emerald-400 to-emerald-500'
      : score >= 0.6
      ? 'from-amber-400 to-amber-500'
      : 'from-gray-300 to-gray-400'

  return (
    <div className="h-1 w-full bg-gray-100 rounded-b-xl overflow-hidden">
      <div
        className={`h-full bg-gradient-to-r ${color} transition-all duration-700`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

function SourceBadge({ source }: { source: Job['source'] }) {
  const cfg = SOURCE_CONFIG[source] ?? SOURCE_CONFIG.naukri
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${cfg.bg} ${cfg.color}`}
    >
      {cfg.label}
    </span>
  )
}

function RelativeTime({ dateStr }: { dateStr: string }) {
  try {
    return (
      <span className="text-xs text-gray-400">
        {formatDistanceToNow(new Date(dateStr), { addSuffix: true })}
      </span>
    )
  } catch {
    return <span className="text-xs text-gray-400">Recently</span>
  }
}

export default function JobCard({ job }: JobCardProps) {
  const [expanded, setExpanded] = useState(false)
  const { openOutreachModal } = useAuth()

  const skills = job.skills_extracted ?? []
  const visibleSkills = skills.slice(0, 4)
  const extraCount = skills.length - 4

  const score = Math.round((job.relevancy_score ?? 0) * 100)

  return (
    <div className="section-card rounded-[1.5rem] overflow-hidden hover:-translate-y-0.5 transition-all duration-200">
      <div
        className="p-6 cursor-pointer"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-2">
              <span className="font-bold text-slate-900 text-lg leading-snug truncate">
                {job.company}
              </span>
              <SourceBadge source={job.source} />
            </div>
            <h3 className="text-base font-semibold text-blue-700 leading-snug mb-3">
              {job.title}
            </h3>

            <div className="flex flex-wrap gap-2 mb-4">
              {job.location && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200 text-xs text-slate-600">
                  <MapPin size={11} /> {job.location}
                </span>
              )}
              {job.experience_required && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200 text-xs text-slate-600">
                  <Briefcase size={11} /> {job.experience_required}
                </span>
              )}
            </div>

            {visibleSkills.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {visibleSkills.map((skill) => (
                  <span
                    key={skill}
                    className="px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 text-xs font-medium border border-blue-100"
                  >
                    {skill}
                  </span>
                ))}
                {extraCount > 0 && (
                  <span className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-500 text-xs font-medium">
                    +{extraCount} more
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="flex flex-col items-end gap-2 shrink-0">
            <div
              className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                score >= 80
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : score >= 60
                  ? 'bg-amber-50 text-amber-700 border border-amber-200'
                  : 'bg-slate-100 text-slate-500 border border-slate-200'
              }`}
            >
              {score}% match
            </div>
            <RelativeTime dateStr={job.posted_at} />
            {expanded ? (
              <ChevronUp size={16} className="text-slate-400" />
            ) : (
              <ChevronDown size={16} className="text-slate-400" />
            )}
          </div>
        </div>
      </div>

      <div className={`jd-expand ${expanded ? 'open' : 'closed'}`}>
        {job.jd_preview && (
          <div className="px-6 pb-4">
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-sm text-slate-600 leading-relaxed">
              {job.jd_preview}
            </div>
          </div>
        )}
      </div>

      <div
        className="px-6 pb-6 flex flex-wrap gap-2"
        onClick={(e) => e.stopPropagation()}
      >
        <a
          href={job.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition-all duration-150 shadow-sm"
        >
          View Job <ExternalLink size={13} />
        </a>

        <button
          onClick={() => openOutreachModal(job)}
          className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-blue-50 hover:bg-blue-100 text-blue-700 text-sm font-semibold transition-all border border-blue-200 shadow-sm"
        >
          Outreach <Send size={13} />
        </button>
      </div>

      <RelevancyBar score={job.relevancy_score} />
    </div>
  )
}
