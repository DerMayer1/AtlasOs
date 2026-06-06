import { cn } from '@/lib/utils'

interface SkeletonProps {
  className?: string
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-zinc-800',
        className,
      )}
    />
  )
}

export function AnalysisCardSkeleton() {
  return (
    <div className="flex items-center justify-between p-4 bg-zinc-900 border border-zinc-800 rounded-lg">
      <div className="space-y-2">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-3 w-20" />
      </div>
      <Skeleton className="h-5 w-16 rounded" />
    </div>
  )
}

export function ResultsSkeleton() {
  return (
    <div className="space-y-16">
      <div className="space-y-3">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-5 w-64" />
        <Skeleton className="h-4 w-full max-w-lg" />
      </div>
      <div className="space-y-3">
        <Skeleton className="h-3 w-28" />
        <div className="grid grid-cols-2 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-4/5" />
            </div>
          ))}
        </div>
      </div>
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <Skeleton className="h-64 w-full" />
      </div>
    </div>
  )
}
