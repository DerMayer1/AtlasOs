import { ResultsSkeleton } from '@/components/Skeleton'

export default function AnalysisLoading() {
  return (
    <div className="min-h-screen bg-black">
      <div className="max-w-4xl mx-auto px-6 py-12">
        <ResultsSkeleton />
      </div>
    </div>
  )
}
