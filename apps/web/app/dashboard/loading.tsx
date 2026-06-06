import { AnalysisCardSkeleton } from '@/components/Skeleton'

export default function DashboardLoading() {
  return (
    <div className="min-h-screen bg-black">
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="flex items-center justify-between mb-10">
          <div className="space-y-2">
            <div className="h-8 w-24 bg-zinc-800 rounded animate-pulse" />
            <div className="h-4 w-36 bg-zinc-800 rounded animate-pulse" />
          </div>
          <div className="h-9 w-32 bg-zinc-800 rounded animate-pulse" />
        </div>
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <AnalysisCardSkeleton key={i} />
          ))}
        </div>
      </div>
    </div>
  )
}
