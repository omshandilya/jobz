'use client'

import { useState } from 'react'
import { Search } from 'lucide-react'

interface SearchBarProps {
  initialQuery?: string
  onSearch: (query: string) => void
  loading?: boolean
}

export default function SearchBar({ initialQuery = '', onSearch, loading }: SearchBarProps) {
  const [query, setQuery] = useState(initialQuery)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) onSearch(query.trim())
  }

  return (
    <form onSubmit={handleSubmit} className="job-search-form w-full">
      <div className="job-search-row flex flex-col sm:flex-row gap-3">
        <div className="job-search-field relative flex-1">
          <Search
            className="search-icon job-search-icon absolute left-4 top-1/2 -translate-y-1/2"
            size={20}
          />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="backend engineer fresher delhi..."
            className="soft-input job-search-input w-full text-base rounded-2xl border shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="primary-button job-search-button disabled:bg-blue-300 text-white font-semibold rounded-2xl transition-all duration-150 flex items-center justify-center gap-2 whitespace-nowrap"
        >
          {loading ? (
            <>
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
              Searching...
            </>
          ) : (
            'Search Jobs'
          )}
        </button>
      </div>
    </form>
  )
}
