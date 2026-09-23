import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link, useNavigate } from "@tanstack/react-router"
import {
  ChevronRight,
  Files,
  Layers,
  Pencil,
  Ruler,
  Trash2,
} from "lucide-react"
import { useEffect, useState } from "react"
import {
  CatalogService,
  FeaturesService,
  type PartDetailPublic,
  PartsService,
} from "@/client"
import { CollapsibleSection } from "@/components/Common/CollapsibleSection"
import {
  FEATURE_COLUMNS,
  FeatureBreadcrumb,
  FeatureSection,
} from "@/components/Features/FeatureLayout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { AddFeatureButton } from "./AddFeatureButton"
import { FeaturePartEvidence } from "./FeaturePartEvidence"
import { MetrologyPage } from "./MetrologyPage"
import type { PartSearch } from "./measurementSelection"
import { PartCover } from "./PartCover"
import { PartReferenceList, type ReferenceChanges } from "./PartReferenceList"
import { PartSetupDialog } from "./PartSetupDialog"

export function PartDetailPage({
  partId,
  search,
}: {
  partId: string
  search: PartSearch
}) {
  const detail = useQuery({
    queryKey: ["parts", "detail", partId],
    queryFn: () => CatalogService.readPartDetail({ partId }),
  })
  if (detail.isPending)
    return (
      <div className="space-y-6">
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  if (detail.error || !detail.data)
    return <p role="alert">{fileErrorMessage(detail.error)}</p>
  return <PartDetailContent key={partId} data={detail.data} search={search} />
}

function PartDetailContent({
  data,
  search,
}: {
  data: PartDetailPublic
  search: PartSearch
}) {
  const { part } = data
  const client = useQueryClient()
  const navigate = useNavigate()
  const [name, setName] = useState(part.name ?? "")
  const [code, setCode] = useState(part.code)
  const [referenceChanges, setReferenceChanges] = useState<ReferenceChanges>({})
  const [pickingFile, setPickingFile] = useState(false)
  const editing = Boolean(search.editar)
  useEffect(() => {
    if (!editing) {
      setName(part.name ?? "")
      setCode(part.code)
      setReferenceChanges({})
    }
  }, [editing, part.name, part.code])
  const setEditing = (value: boolean) =>
    void navigate({
      to: "/parts/$partId",
      params: { partId: part.id },
      search: { ...search, editar: value ? true : undefined },
      replace: true,
      resetScroll: false,
    })
  const invalidate = () =>
    Promise.all(
      [
        "parts",
        "features",
        "part-evidence",
        "feature-evidence",
        "metrology-filters",
      ].map((key) => client.invalidateQueries({ queryKey: [key] })),
    )
  const save = useMutation({
    mutationFn: () =>
      PartsService.updatePart({
        partId: part.id,
        requestBody: {
          name: name.trim(),
          code: code.trim(),
          ...(Object.keys(referenceChanges).length
            ? { references: Object.values(referenceChanges) }
            : {}),
        },
      }),
    onSuccess: async () => {
      await invalidate()
      setEditing(false)
    },
  })
  const membership = useMutation({
    mutationFn: async ({
      featureId,
      remove,
    }: {
      featureId: string
      remove?: boolean
    }) => {
      if (remove)
        await FeaturesService.unlinkFeaturePart({ featureId, partId: part.id })
      else await FeaturesService.linkFeaturePart({ featureId, partId: part.id })
    },
    onSuccess: invalidate,
  })
  return (
    <div className="flex min-w-0 flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <FeatureBreadcrumb kind="part" name={part.name ?? part.code} />
        <div className="flex flex-wrap items-center gap-2">
          <PartSetupDialog part={part} />
          {editing ? (
            <>
              <Button
                variant="outline"
                disabled={save.isPending}
                onClick={() => {
                  save.reset()
                  setEditing(false)
                }}
              >
                Cancelar
              </Button>
              <Button
                disabled={
                  save.isPending || pickingFile || !name.trim() || !code.trim()
                }
                onClick={() => save.mutate()}
              >
                {save.isPending ? "Guardando…" : "Guardar cambios"}
              </Button>
            </>
          ) : (
            <Button
              variant="outline"
              className="border-primary text-primary hover:text-primary"
              onClick={() => setEditing(true)}
            >
              <Pencil /> Editar pieza
            </Button>
          )}
        </div>
      </div>
      {save.error && (
        <p role="alert" className="text-sm text-destructive">
          {fileErrorMessage(save.error)}
        </p>
      )}
      <div className="flex flex-col gap-4 rounded-lg border bg-card p-4 sm:flex-row sm:gap-6 sm:p-5">
        <PartCover part={part} />
        <div className="min-w-0 flex-1 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Pieza
          </p>
          {editing ? (
            <>
              <Input
                aria-label="Nombre de la pieza"
                value={name}
                disabled={save.isPending}
                maxLength={255}
                onChange={(event) => setName(event.target.value)}
                className="h-auto py-1 text-2xl font-bold tracking-tight sm:text-3xl md:text-3xl"
              />
              <Input
                aria-label="Código de la pieza"
                value={code}
                disabled={save.isPending}
                maxLength={64}
                onChange={(event) => setCode(event.target.value)}
                className="max-w-48 text-base text-muted-foreground md:text-base"
              />
            </>
          ) : (
            <>
              <h1 className="break-words text-2xl font-bold tracking-tight sm:text-3xl">
                {part.name ?? part.code}
              </h1>
              <p className="text-muted-foreground">{part.code}</p>
            </>
          )}
        </div>
      </div>
      <div className={FEATURE_COLUMNS}>
        <section
          id="cotas"
          className="min-w-0 scroll-mt-6"
          aria-label="Cotas de la pieza"
        >
          <FeatureSection
            title="Cotas"
            count={part.characteristic_count}
            icon={<Ruler className="size-5 shrink-0 text-muted-foreground" />}
          >
            <MetrologyPage partId={part.id} search={search} embedded />
          </FeatureSection>
        </section>
        <div className="min-w-0 space-y-5">
          <FeatureSection
            title="Features"
            count={data.features.length}
            icon={<Layers className="size-5 shrink-0 text-muted-foreground" />}
          >
            <div className="space-y-3">
              {data.features.map((feature) => (
                <section
                  key={feature.id}
                  aria-label={`Feature ${feature.name}`}
                >
                  <CollapsibleSection
                    compact
                    title={feature.name}
                    className="bg-muted/20"
                    storageKey={`piece-feature:${part.id}:${feature.id}`}
                    headerContent={
                      <Link
                        to="/features/$featureId"
                        params={{ featureId: feature.id }}
                        aria-label={`Abrir ${feature.name}`}
                        className="flex h-7 min-w-0 flex-1 items-center text-lg font-semibold hover:underline"
                      >
                        <span className="truncate">{feature.name}</span>
                      </Link>
                    }
                    actions={
                      <div className="flex shrink-0 items-center gap-1">
                        {editing && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-7 shrink-0 text-destructive"
                            aria-label={`Desvincular ${feature.name}`}
                            disabled={membership.isPending}
                            onClick={() =>
                              membership.mutate({
                                featureId: feature.id,
                                remove: true,
                              })
                            }
                          >
                            <Trash2 className="size-3.5" />
                          </Button>
                        )}
                        <Button
                          asChild
                          variant="ghost"
                          size="sm"
                          className="h-7 shrink-0 gap-1 px-1 text-primary hover:text-primary"
                        >
                          <Link
                            to="/features/$featureId"
                            params={{ featureId: feature.id }}
                            aria-label={`Ver feature ${feature.name}`}
                          >
                            Ver feature <ChevronRight className="size-4" />
                          </Link>
                        </Button>
                      </div>
                    }
                  >
                    <div className="border-t pt-2">
                      <FeaturePartEvidence
                        feature={feature}
                        partId={part.id}
                        onSelectCota={(cota) => {
                          void navigate({
                            to: "/parts/$partId",
                            params: { partId: part.id },
                            search: {
                              editar: search.editar,
                              cota: cota.code,
                              revision: cota.revision,
                            },
                            resetScroll: false,
                          })
                          document.getElementById("cotas")?.scrollIntoView({
                            behavior: "smooth",
                            block: "start",
                          })
                        }}
                      />
                    </div>
                  </CollapsibleSection>
                </section>
              ))}
              {!data.features.length && (
                <p className="text-sm text-muted-foreground">
                  Sin features vinculados.
                </p>
              )}
              {editing && (
                <AddFeatureButton
                  linkedIds={data.features.map((feature) => feature.id)}
                  disabled={membership.isPending || save.isPending}
                  onSelect={(featureId) => membership.mutate({ featureId })}
                />
              )}
              {membership.error && (
                <p role="alert" className="text-sm text-destructive">
                  {fileErrorMessage(membership.error)}
                </p>
              )}
            </div>
          </FeatureSection>
          <FeatureSection
            title="Archivos"
            count={data.references.length}
            icon={<Files className="size-5 shrink-0 text-muted-foreground" />}
          >
            <PartReferenceList
              data={data}
              editing={editing}
              changes={referenceChanges}
              onChange={(choice) =>
                setReferenceChanges((current) => ({
                  ...current,
                  [choice.kind]: choice,
                }))
              }
              saving={save.isPending}
              onPickingChange={setPickingFile}
            />
          </FeatureSection>
        </div>
      </div>
    </div>
  )
}
