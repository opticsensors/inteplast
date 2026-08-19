import { useQuery } from "@tanstack/react-query"
import { Lightbulb, Package2, TriangleAlert } from "lucide-react"

import type { NoteKind } from "@/client"
import { CollapsibleSection } from "@/components/Common/CollapsibleSection"
import { RichTextView } from "@/components/Common/RichText"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { CATEGORY_LABELS } from "./constants"
import { FeatureThumbnail } from "./FeatureCard"
import { PartAssetMatrix } from "./PartAssetMatrix"
import { featureQueryOptions } from "./queries"

interface FeatureDetailDialogProps {
  featureId: string | null
  onOpenChange: (open: boolean) => void
}

/** Ficha completa de un feature: warnings, lessons learned y piezas ejemplo. */
export function FeatureDetailDialog({
  featureId,
  onOpenChange,
}: FeatureDetailDialogProps) {
  const { data: feature, isLoading } = useQuery({
    ...featureQueryOptions(featureId ?? ""),
    enabled: Boolean(featureId),
  })

  const notesOf = (kind: NoteKind) =>
    (feature?.notes ?? []).filter((note) => note.kind === kind)

  return (
    <Dialog open={Boolean(featureId)} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        {isLoading || !feature ? (
          <div className="space-y-3">
            <Skeleton className="h-8 w-1/2" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : (
          <>
            <DialogHeader>
              <div className="flex items-start gap-3">
                <FeatureThumbnail
                  feature={feature}
                  className="size-28 sm:size-32"
                />
                <div className="min-w-0 flex-1 space-y-1 text-left">
                  <DialogTitle>{feature.name}</DialogTitle>
                  <DialogDescription>
                    {feature.description || "Sin descripcion"}
                  </DialogDescription>
                  <div className="flex flex-wrap gap-1 pt-1">
                    {feature.category && (
                      <Badge variant="secondary">
                        {CATEGORY_LABELS[feature.category]}
                      </Badge>
                    )}
                    {(feature.tags ?? []).map((tag) => (
                      <Badge key={tag} variant="outline">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            </DialogHeader>

            <div className="space-y-3">
              <CollapsibleSection
                title="Warnings"
                icon={<TriangleAlert className="size-4 text-amber-500" />}
              >
                {notesOf("warning").length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    Sin advertencias documentadas.
                  </p>
                ) : (
                  notesOf("warning").map((note) => (
                    <CollapsibleSection
                      key={note.id}
                      title={note.title}
                      defaultOpen={false}
                    >
                      <RichTextView value={note.body} />
                    </CollapsibleSection>
                  ))
                )}
              </CollapsibleSection>

              <CollapsibleSection
                title="Lessons Learned"
                icon={<Lightbulb className="size-4 text-yellow-500" />}
              >
                {notesOf("lesson").length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    Sin lecciones aprendidas documentadas.
                  </p>
                ) : (
                  notesOf("lesson").map((note) => (
                    <CollapsibleSection
                      key={note.id}
                      title={note.title}
                      defaultOpen={false}
                    >
                      <RichTextView value={note.body} />
                    </CollapsibleSection>
                  ))
                )}
              </CollapsibleSection>

              <CollapsibleSection
                title="Piezas ejemplo"
                icon={<Package2 className="size-4 text-muted-foreground" />}
              >
                <PartAssetMatrix feature={feature} />
              </CollapsibleSection>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
