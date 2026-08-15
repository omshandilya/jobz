'use client'

import { useState, useEffect, useCallback, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { Search } from 'lucide-react'
import { searchJobs } from '@/lib/api'
import type { Job, SortMode, SourceFilter } from '@/types/job'
import { AuthProvider } from '@/context/AuthContext'
import Navbar from '@/components/Navbar'
import SearchBar from '@/components/SearchBar'
import FilterBar from '@/components/FilterBar'
import JobCard from '@/components/JobCard'
import JobCardSkeleton from '@/components/JobCardSkeleton'
import AuthModal from '@/components/AuthModal'
import SettingsModal from '@/components/SettingsModal'
import OutreachModal from '@/components/OutreachModal'

const SUGGESTED = [
  'AI engineer delhi',
  'backend fresher bangalore',
  'frontend developer mumbai',
  'python developer remote',
  'data engineer hyderabad',
]

function EmptyState({ onSuggest }: { onSuggest: (q: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-16 h-16 rounded-2xl bg-indigo-50 flex items-center justify-center mb-4">
        <Search size={28} className="text-indigo-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-800 mb-1">No jobs found</h3>
      <p className="text-gray-500 text-sm mb-6">Try different keywords or broaden your search</p>
      <div className="flex flex-wrap gap-2 justify-center">
        {SUGGESTED.map((s) => (
          <button
            key={s}
            onClick={() => onSuggest(s)}
            className="px-4 py-2 rounded-full bg-white border border-slate-200 text-sm text-blue-700 hover:border-blue-300 hover:bg-blue-50 transition-all font-medium shadow-sm"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}

function HomeContent() {
  const router = useRouter()
  const params = useSearchParams()

  const [query, setQuery] = useState(params.get('q') ?? '')
  const [location, setLocation] = useState(params.get('location') ?? 'india')
  const [dateHours, setDateHours] = useState(Number(params.get('hours') ?? 720))
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all')
  const [sortMode, setSortMode] = useState<SortMode>('relevant')

  const [allJobs, setAllJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const doSearch = useCallback(
    async (q: string, loc: string, hours: number) => {
      if (!q.trim()) return
      setLoading(true)
      setSearched(true)
      const toastId = toast.loading('Searching for jobs...')
      try {
        const res = await searchJobs(q, loc, hours)
        setAllJobs(res.results)
        toast.dismiss(toastId)
        if (res.count > 0) {
          toast.success(`Found ${res.count} job${res.count !== 1 ? 's' : ''}`)
        } else {
          toast.info('No jobs found. Try different keywords.')
        }
      } catch {
        toast.dismiss(toastId)
        toast.error('Search failed. Check if backend is running.')
        setAllJobs([])
      } finally {
        setLoading(false)
      }
    },
    []
  )

  // Auto-trigger on load if URL params are present
  useEffect(() => {
    const q = params.get('q')
    const loc = params.get('location') ?? 'india'
    const hours = Number(params.get('hours') ?? 720)
    if (q) {
      setQuery(q)
      setLocation(loc)
      setDateHours(hours)
      doSearch(q, loc, hours)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSearch = (q: string) => {
    setQuery(q)
    const url = new URLSearchParams({ q, location, hours: String(dateHours) })
    router.push(`?${url.toString()}`)
    doSearch(q, location, dateHours)
  }

  const handleSuggest = (q: string) => {
    setQuery(q)
    const url = new URLSearchParams({ q, location, hours: String(dateHours) })
    router.push(`?${url.toString()}`)
    doSearch(q, location, dateHours)
  }

  // Client-side filter + sort
  const filteredJobs = allJobs
    .filter((j) => sourceFilter === 'all' || j.source === sourceFilter)
    .sort((a, b) => {
      if (sortMode === 'relevant') return b.relevancy_score - a.relevancy_score
      return new Date(b.posted_at).getTime() - new Date(a.posted_at).getTime()
    })

  return (
    <div className="app-shell min-h-screen">
      <Navbar>
        {searched && (
          <SearchBar initialQuery={query} onSearch={handleSearch} loading={loading} />
        )}
      </Navbar>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10 space-y-8">
        {/* Hero section — shown before first search */}
        {!searched && (
          <div className="section-card relative overflow-hidden rounded-[2rem] px-6 py-12 sm:px-10 sm:py-16 text-center">
            <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.08),transparent_40%)]" />
            <div className="relative">
              <div className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-4 py-1 text-xs font-semibold text-blue-700 mb-6">
                AI-powered job search and outreach
              </div>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-slate-900 tracking-tight leading-tight mb-4">
                Find jobs.{' '}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 via-sky-600 to-cyan-600">
                  Reach the right people.
                </span>
              </h1>
              <p className="mx-auto max-w-2xl text-base sm:text-lg text-slate-600 mb-8">
                Search across Naukri and Internshala with less clutter, clearer filters, and a calmer results view.
              </p>
              <div className="max-w-3xl mx-auto">
                <SearchBar initialQuery={query} onSearch={handleSearch} loading={loading} />
              </div>
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {SUGGESTED.map((s) => (
                  <button
                    key={s}
                    onClick={() => handleSuggest(s)}
                    className="px-4 py-2 rounded-full bg-white border border-slate-200 text-sm text-blue-700 hover:border-blue-300 hover:bg-blue-50 transition-all font-medium shadow-sm"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Filter bar — shown after first search */}
        {searched && (
          <div className="section-card rounded-2xl px-4 py-4 sm:px-5 sm:py-5">
            <FilterBar
              location={location}
              onLocationChange={setLocation}
              dateHours={dateHours}
              onDateHoursChange={setDateHours}
              sourceFilter={sourceFilter}
              onSourceFilterChange={setSourceFilter}
              sortMode={sortMode}
              onSortModeChange={setSortMode}
              totalCount={filteredJobs.length}
            />
          </div>
        )}

        {/* Loading skeletons */}
        {loading && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 xl:gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <JobCardSkeleton key={i} />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && searched && filteredJobs.length === 0 && (
          <EmptyState onSuggest={handleSuggest} />
        )}

        {/* Job results grid */}
        {!loading && filteredJobs.length > 0 && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 xl:gap-6">
            {filteredJobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </div>

      {/* Global modals */}
      <AuthModal />
      <SettingsModal />
      <OutreachModal />
    </div>
  )
}

export default function Home() {
  return (
    <AuthProvider>
      <Suspense>
        <HomeContent />
      </Suspense>
    </AuthProvider>
  )
}
