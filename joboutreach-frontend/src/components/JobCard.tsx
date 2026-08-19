'use client'

import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { MapPin, Briefcase, ExternalLink, ChevronDown, ChevronUp, Send, Building2 } from 'lucide-react'
import type { Job } from '@/types/job'
import { useAuth } from '@/context/AuthContext'

interface JobCardProps {
  job: Job
}

const SOURCE_CONFIG: Record<Job['source'], { label: string; color: string; bg: string }> = {
  naukri: { label: 'Naukri', color: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-200' },
  internshala: { label: 'Internshala', color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200' },
  indeed: { label: 'Indeed', color: 'text-indigo-700', bg: 'bg-indigo-50 border-indigo-200' },
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
    <div className="relevancy-track h-1 w-full rounded-b-xl overflow-hidden">
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
  let relativeTime = 'Recently'
  try {
    relativeTime = formatDistanceToNow(new Date(dateStr), { addSuffix: true })
  } catch { /* Keep the safe fallback for invalid source dates. */ }
  return <span className="text-xs text-gray-400">{relativeTime}</span>
}

export default function JobCard({ job }: JobCardProps) {
  const [expanded, setExpanded] = useState(false)
  const { openOutreachModal } = useAuth()

  const skills = job.skills_extracted ?? []
  const visibleSkills = skills.slice(0, 4)
  const extraCount = skills.length - 4

  const score = Math.round((job.relevancy_score ?? 0) * 100)

  return (
    <article className="job-card section-card rounded-[1.5rem] overflow-hidden hover:-translate-y-0.5 transition-all duration-200">
      <div className="job-card-body p-5 sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h3 className="job-title job-title-clamp text-base font-semibold leading-snug mb-2 break-words">
              {job.title}
            </h3>
            <div className="job-company-row flex items-center gap-2 min-w-0 mb-3">
              <Building2 size={14} className="shrink-0" />
              <span className="job-company truncate">{job.company}</span>
              <SourceBadge source={job.source} />
            </div>

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
                    className="skill-tag px-2.5 py-1 rounded-lg text-xs font-medium"
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

          <div className="job-card-score flex flex-col items-end gap-2 shrink-0">
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
          </div>
        </div>
      </div>

      <div className={`jd-expand ${expanded ? 'open' : 'closed'}`}>
        {job.jd_preview && (
          <div className="px-5 sm:px-6 pb-4">
            <div className="job-description job-description-clamp p-4 rounded-2xl text-sm leading-relaxed break-words">
              {job.jd_preview}
            </div>
          </div>
        )}
      </div>

      <div
        className="job-card-actions px-5 sm:px-6 pb-5 sm:pb-6 flex flex-wrap gap-2"
        onClick={(e) => e.stopPropagation()}
      >
        {job.jd_preview && (
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            className="details-button inline-flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-sm font-semibold"
            aria-expanded={expanded}
          >
            {expanded ? 'Hide details' : 'View details'}
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        )}
        <a
          href={job.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="primary-button inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-white text-sm font-semibold transition-all duration-150"
        >
          View Job <ExternalLink size={13} />
        </a>

        <button
          onClick={() => openOutreachModal(job)}
          className="outreach-button inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all"
        >
          Outreach <Send size={13} />
        </button>
      </div>

      <RelevancyBar score={job.relevancy_score} />
    </article>
  )
}
