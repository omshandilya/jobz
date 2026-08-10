'use client'

import { useState, useEffect, useCallback, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { Sparkles, Search } from 'lucide-react'
import { searchJobs } from '@/lib/api'
import type { Job, SortMode, SourceFilter } from '@/types/job'
import SearchBar from '@/components/SearchBar'
import FilterBar from '@/components/FilterBar'
import JobCard from '@/components/JobCard'
import JobCardSkeleton from '@/components/JobCardSkeleton'

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
            className="px-4 py-2 rounded-full bg-white border border-gray-200 text-sm text-indigo-600 hover:border-indigo-400 hover:bg-indigo-50 transition-all font-medium shadow-sm"
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

  // Auto-trigger on load if params present
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
    <main className="min-h-screen" style={{ background: 'var(--background)' }}>
      {/* Header */}
      <div className="bg-white border-b border-gray-100 sticky top-0 z-30 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-4">
          <div className="flex items-center gap-2 shrink-0">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center shadow-sm">
              <Sparkles size={18} className="text-white" />
            </div>
            <span className="text-2xl font-black text-gray-900 tracking-tight">Jobz</span>
          </div>
          <div className="flex-1 max-w-2xl">
            <SearchBar initialQuery={query} onSearch={handleSearch} loading={loading} />
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Hero — shown before first search */}
        {!searched && (
          <div className="text-center py-12">
            <h1 className="text-5xl font-black text-gray-900 tracking-tight mb-3">
              Find jobs.{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-500 to-purple-600">
                Reach the right people.
              </span>
            </h1>
            <p className="text-lg text-gray-500 mb-8">
              AI-powered job search across Naukri, Internshala & more — with smart relevancy scoring.
            </p>
            <div className="max-w-2xl mx-auto">
              <SearchBar initialQuery={query} onSearch={handleSearch} loading={loading} />
            </div>
            <div className="mt-6 flex flex-wrap gap-2 justify-center">
              {SUGGESTED.map((s) => (
                <button
                  key={s}
                  onClick={() => handleSuggest(s)}
                  className="px-4 py-2 rounded-full bg-white border border-gray-200 text-sm text-indigo-600 hover:border-indigo-400 hover:bg-indigo-50 transition-all font-medium shadow-sm"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Filters */}
        {searched && (
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
        )}

        {/* Results */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <JobCardSkeleton key={i} />
            ))}
          </div>
        )}

        {!loading && searched && filteredJobs.length === 0 && (
          <EmptyState onSuggest={handleSuggest} />
        )}

        {!loading && filteredJobs.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredJobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </div>
    </main>
  )
}

export default function Home() {
  return (
    <Suspense>
      <HomeContent />
    </Suspense>
  )
}
