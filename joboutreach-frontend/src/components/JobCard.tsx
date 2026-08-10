'use client'

import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { MapPin, Briefcase, ExternalLink, ChevronDown, ChevronUp, Send } from 'lucide-react'
import type { Job } from '@/types/job'

interface JobCardProps {
  job: Job
}

const SOURCE_CONFIG: Record<Job['source'], { label: string; color: string; bg: string }> = {
  naukri: { label: 'Naukri', color: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-200' },
  internshala: { label: 'Internshala', color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200' },
  indeed: { label: 'Indeed', color: 'text-orange-700', bg: 'bg-orange-50 border-orange-200' },
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

  const skills = job.skills_extracted ?? []
  const visibleSkills = skills.slice(0, 4)
  const extraCount = skills.length - 4

  const score = Math.round((job.relevancy_score ?? 0) * 100)

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition-all duration-200">
      {/* Card body — clickable to expand JD */}
      <div
        className="p-5 cursor-pointer"
        onClick={() => setExpanded((v) => !v)}
      >
        {/* Top row */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className="font-bold text-gray-900 text-lg leading-snug truncate">
                {job.company}
              </span>
              <SourceBadge source={job.source} />
            </div>
            <h3 className="text-base font-semibold text-indigo-700 leading-snug mb-2">
              {job.title}
            </h3>

            {/* Pills */}
            <div className="flex flex-wrap gap-2 mb-3">
              {job.location && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-gray-50 border border-gray-200 text-xs text-gray-600">
                  <MapPin size={11} /> {job.location}
                </span>
              )}
              {job.experience_required && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-gray-50 border border-gray-200 text-xs text-gray-600">
                  <Briefcase size={11} /> {job.experience_required}
                </span>
              )}
            </div>

            {/* Skills */}
            {visibleSkills.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {visibleSkills.map((skill) => (
                  <span
                    key={skill}
                    className="px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 text-xs font-medium border border-indigo-100"
                  >
                    {skill}
                  </span>
                ))}
                {extraCount > 0 && (
                  <span className="px-2 py-0.5 rounded-md bg-gray-100 text-gray-500 text-xs font-medium">
                    +{extraCount} more
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Score badge + time */}
          <div className="flex flex-col items-end gap-2 shrink-0">
            <div
              className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                score >= 80
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : score >= 60
                  ? 'bg-amber-50 text-amber-700 border border-amber-200'
                  : 'bg-gray-100 text-gray-500 border border-gray-200'
              }`}
            >
              {score}% match
            </div>
            <RelativeTime dateStr={job.posted_at} />
            {expanded ? (
              <ChevronUp size={16} className="text-gray-400" />
            ) : (
              <ChevronDown size={16} className="text-gray-400" />
            )}
          </div>
        </div>
      </div>

      {/* Expandable JD preview */}
      <div className={`jd-expand ${expanded ? 'open' : 'closed'}`}>
        {job.jd_preview && (
          <div className="px-5 pb-3">
            <div className="p-3 rounded-lg bg-gray-50 border border-gray-100 text-sm text-gray-600 leading-relaxed">
              {job.jd_preview}
            </div>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div
        className="px-5 pb-5 flex gap-2"
        onClick={(e) => e.stopPropagation()}
      >
        <a
          href={job.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold transition-all duration-150 shadow-sm"
        >
          View Job <ExternalLink size={13} />
        </a>

        {/* Outreach button — disabled with tooltip */}
        <div className="relative group">
          <button
            disabled
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gray-100 text-gray-400 text-sm font-semibold cursor-not-allowed border border-gray-200"
          >
            Outreach <Send size={13} />
          </button>
          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-gray-800 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
            Coming in next phase
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
          </div>
        </div>
      </div>

      {/* Relevancy bar at bottom */}
      <RelevancyBar score={job.relevancy_score} />
    </div>
  )
}
