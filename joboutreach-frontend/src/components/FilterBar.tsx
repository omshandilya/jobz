'use client'

import { MapPin, Clock, SlidersHorizontal, ArrowDownUp } from 'lucide-react'
import type { SortMode, SourceFilter } from '@/types/job'

interface FilterBarProps {
  location: string
  onLocationChange: (v: string) => void
  dateHours: number
  onDateHoursChange: (v: number) => void
  sourceFilter: SourceFilter
  onSourceFilterChange: (v: SourceFilter) => void
  sortMode: SortMode
  onSortModeChange: (v: SortMode) => void
  totalCount: number
}

const SOURCE_TABS: { label: string; value: SourceFilter }[] = [
  { label: 'All', value: 'all' },
  { label: 'Naukri', value: 'naukri' },
  { label: 'Internshala', value: 'internshala' },
  { label: 'Indeed', value: 'indeed' },
]

const DATE_OPTIONS = [
  { label: 'Last 24h', value: 24 },
  { label: 'Last 48h', value: 48 },
  { label: 'Last 7 days', value: 168 },
  { label: 'Last 30 days', value: 720 },
]

export default function FilterBar({
  location,
  onLocationChange,
  dateHours,
  onDateHoursChange,
  sourceFilter,
  onSourceFilterChange,
  sortMode,
  onSortModeChange,
  totalCount,
}: FilterBarProps) {
  return (
    <div className="space-y-3">
      {/* Filters row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Location */}
        <div className="relative">
          <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={15} />
          <input
            type="text"
            value={location}
            onChange={(e) => onLocationChange(e.target.value)}
            placeholder="Location (e.g. delhi)"
            className="pl-9 pr-4 py-2 text-sm rounded-lg border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 w-44"
          />
        </div>

        {/* Date posted */}
        <div className="relative">
          <Clock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={15} />
          <select
            value={dateHours}
            onChange={(e) => onDateHoursChange(Number(e.target.value))}
            className="pl-9 pr-4 py-2 text-sm rounded-lg border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 appearance-none cursor-pointer"
          >
            {DATE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Sort */}
        <div className="relative">
          <ArrowDownUp className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={15} />
          <select
            value={sortMode}
            onChange={(e) => onSortModeChange(e.target.value as SortMode)}
            className="pl-9 pr-4 py-2 text-sm rounded-lg border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 appearance-none cursor-pointer"
          >
            <option value="relevant">Most Relevant</option>
            <option value="recent">Most Recent</option>
          </select>
        </div>

        {/* Results count */}
        {totalCount > 0 && (
          <span className="ml-auto text-sm text-gray-500 font-medium">
            {totalCount} jobs found
          </span>
        )}
      </div>

      {/* Source tabs */}
      <div className="flex items-center gap-1">
        <SlidersHorizontal size={14} className="text-gray-400 mr-1" />
        {SOURCE_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => onSourceFilterChange(tab.value)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-150 ${
              sourceFilter === tab.value
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-white text-gray-600 border border-gray-200 hover:border-indigo-300 hover:text-indigo-600'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  )
}
