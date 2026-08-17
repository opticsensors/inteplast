import { useQuery } from "@tanstack/react-query"
import { Download, Lightbulb, Package2, TriangleAlert } from "lucide-react"

import type { AssetKind, FeatureAssetPublic, NoteKind } from "@/client"
import { CollapsibleSection } from "@/components/Common/CollapsibleSection"
import { RichTextView } from "@/components/Common/RichText"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { fileUrl } from "@/utils"
import { ASSET_KIND_LABELS, ASSET_KINDS, CATEGORY_LABELS } from "./constants"
import { ASSET_ICONS, FeatureThumbnail } from "./FeatureCard"
import { featureQueryOptions } from "./queries"

function AssetRow({ asset }: { asset: FeatureAssetPublic }) {
  const Icon = ASSET_ICONS[asset.kind]
  return (
    <div className="flex items-center gap-2 rounded-md border px-2 py-1.5 text-sm">
      <Icon className="size-4 shrink-0 text-muted-foreground" />
      <span className="truncate">{asset.name}</span>
      {asset.part_ref && (
        <span className="ml-auto shrink-0 text-xs text-muted-foreground">
          {asset.part_ref}
        </span>
      )}
      {asset.file && (
        <Button variant="ghost" size="icon" className="size-7 shrink-0" asChild>
          <a
            href={fileUrl(asset.file.id)}
            download={asset.file.filename}
            target="_blank"
            rel="noreferrer"
          >
            <Download className="size-3.5" />
            <span className="sr-only">Descargar {asset.name}</span>
          </a>
        </Button>
      )}
    </div>
  )
}

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
  const assetsOf = (kind: AssetKind) =>
    (feature?.assets ?? []).filter((asset) => asset.kind === kind)

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
                <FeatureThumbnail feature={feature} className="size-20" />
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
                {(feature.assets ?? []).length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    Sin piezas de referencia adjuntas.
                  </p>
                ) : (
                  ASSET_KINDS.filter((kind) => assetsOf(kind).length > 0).map(
                    (kind) => (
                      <CollapsibleSection
                        key={kind}
                        title={ASSET_KIND_LABELS[kind]}
                      >
                        {assetsOf(kind).map((asset) => (
                          <AssetRow key={asset.id} asset={asset} />
                        ))}
                      </CollapsibleSection>
                    ),
                  )
                )}
              </CollapsibleSection>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
