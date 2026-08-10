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
    <form onSubmit={handleSubmit} className="w-full">
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search
            className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400"
            size={20}
          />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="backend engineer fresher delhi..."
            className="w-full pl-12 pr-4 py-4 text-base rounded-xl border border-gray-200 bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition placeholder:text-gray-400"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-7 py-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white font-semibold rounded-xl transition-all duration-150 flex items-center gap-2 whitespace-nowrap shadow-sm"
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
