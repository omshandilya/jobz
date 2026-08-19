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
    <div className="space-y-4">
      <div className="flex flex-col xl:flex-row xl:items-center gap-3">
        <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <MapPin className="filter-icon absolute left-3 top-1/2 -translate-y-1/2" size={15} />
          <input
            type="text"
            value={location}
            onChange={(e) => onLocationChange(e.target.value)}
            placeholder="Location (e.g. delhi)"
            className="soft-input w-full sm:w-52 pl-9 pr-4 py-2.5 text-sm rounded-xl border focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="relative">
          <Clock className="filter-icon absolute left-3 top-1/2 -translate-y-1/2" size={15} />
          <select
            value={dateHours}
            onChange={(e) => onDateHoursChange(Number(e.target.value))}
            className="soft-input pl-9 pr-4 py-2.5 text-sm rounded-xl border focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer"
          >
            {DATE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="relative">
          <ArrowDownUp className="filter-icon absolute left-3 top-1/2 -translate-y-1/2" size={15} />
          <select
            value={sortMode}
            onChange={(e) => onSortModeChange(e.target.value as SortMode)}
            className="soft-input pl-9 pr-4 py-2.5 text-sm rounded-xl border focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer"
          >
            <option value="relevant">Most Relevant</option>
            <option value="recent">Most Recent</option>
          </select>
        </div>
        </div>

        {totalCount > 0 && (
          <span className="count-pill xl:ml-auto text-sm font-medium px-3 py-1.5 rounded-full">
            {totalCount} jobs found
          </span>
        )}
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <SlidersHorizontal size={14} className="filter-icon mr-1" />
        {SOURCE_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => onSourceFilterChange(tab.value)}
            className={`px-3.5 py-2 rounded-full text-xs font-semibold transition-all duration-150 ${
              sourceFilter === tab.value
                ? 'source-tab-active text-white shadow-sm'
                : 'source-tab'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  )
}
