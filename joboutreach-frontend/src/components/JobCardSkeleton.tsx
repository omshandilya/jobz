export default function JobCardSkeleton() {
  return (
    <div className="section-card rounded-[1.5rem] overflow-hidden">
      <div className="p-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="flex-1 space-y-2">
            <div className="flex gap-2">
              <div className="shimmer h-5 w-36 rounded-md" />
              <div className="shimmer h-5 w-16 rounded-full" />
            </div>
            <div className="shimmer h-4 w-56 rounded-md" />
          </div>
          <div className="shimmer h-7 w-16 rounded-full" />
        </div>

        <div className="flex gap-2 mb-4">
          <div className="shimmer h-6 w-24 rounded-full" />
          <div className="shimmer h-6 w-20 rounded-full" />
        </div>

        <div className="flex gap-2">
          <div className="shimmer h-5 w-14 rounded-md" />
          <div className="shimmer h-5 w-18 rounded-md" />
          <div className="shimmer h-5 w-12 rounded-md" />
        </div>
      </div>

      <div className="px-6 pb-6 flex gap-2">
        <div className="shimmer h-9 w-28 rounded-lg" />
        <div className="shimmer h-9 w-24 rounded-lg" />
      </div>

      <div className="shimmer h-1 w-full" />
    </div>
  )
}
