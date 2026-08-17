import { Skeleton } from "@/components/ui/skeleton"

const PendingFeatures = ({ count = 4 }: { count?: number }) => (
  <div className="space-y-2">
    {Array.from({ length: count }, (_, index) => index).map((index) => (
      <div key={index} className="flex gap-3 rounded-lg border p-3">
        <Skeleton className="size-16 shrink-0 rounded-md" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-5 w-52" />
        </div>
      </div>
    ))}
  </div>
)

export default PendingFeatures
