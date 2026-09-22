import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link, useNavigate } from "@tanstack/react-router"
import { Download, Files, Layers, Ruler, Trash2 } from "lucide-react"
import { useEffect, useState } from "react"
import {
  CatalogService,
  FeaturesService,
  type PartDetailPublic,
  PartsService,
} from "@/client"
import { CollapsibleSection } from "@/components/Common/CollapsibleSection"
import { FileLink } from "@/components/Common/FileLink"
import { SearchSelect } from "@/components/Common/SearchSelect"
import { ASSET_ICONS, ASSET_KIND_LABELS } from "@/components/Features/constants"
import { FeatureActions } from "@/components/Features/FeatureActions"
import { FeatureCard } from "@/components/Features/FeatureCard"
import { featureFiltersQueryOptions } from "@/components/Features/queries"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { MetrologyPage } from "./MetrologyPage"
import type { PartSearch } from "./measurementSelection"
import { PartCover } from "./PartCover"
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
  const editing = Boolean(search.editar)
  useEffect(() => {
    if (!editing) {
      setName(part.name ?? "")
      setCode(part.code)
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
        requestBody: { name: name.trim(), code: code.trim() },
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
  const filters = useQuery({
    ...featureFiltersQueryOptions(),
    enabled: editing,
  })
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap justify-end gap-2">
        <PartSetupDialog part={part} />
        {editing ? (
          <>
            <Button
              variant="outline"
              size="sm"
              disabled={save.isPending}
              onClick={() => {
                save.reset()
                setEditing(false)
              }}
            >
              Cancelar
            </Button>
            <Button
              size="sm"
              disabled={save.isPending || !name.trim() || !code.trim()}
              onClick={() => save.mutate()}
            >
              {save.isPending ? "Guardando…" : "Guardar"}
            </Button>
          </>
        ) : (
          <FeatureActions variant="outline" onEdit={() => setEditing(true)} />
        )}
      </div>
      {save.error && (
        <p role="alert" className="text-sm text-destructive">
          {fileErrorMessage(save.error)}
        </p>
      )}
      <div className="flex gap-4 rounded-lg border p-4 sm:gap-6 sm:p-6">
        <PartCover part={part} />
        <div className="min-w-0 flex-1 space-y-3">
          {editing ? (
            <>
              <Input
                aria-label="Nombre de la pieza"
                value={name}
                maxLength={255}
                onChange={(event) => setName(event.target.value)}
                className="h-auto py-1 text-2xl font-bold tracking-tight md:text-2xl"
              />
              <Input
                aria-label="Código de la pieza"
                value={code}
                maxLength={64}
                onChange={(event) => setCode(event.target.value)}
                className="max-w-48 font-mono"
              />
            </>
          ) : (
            <>
              <h1 className="break-words text-2xl font-bold tracking-tight sm:text-3xl">
                {part.name ?? part.code}
              </h1>
              <p className="font-mono text-muted-foreground">{part.code}</p>
            </>
          )}
          <p className="text-sm text-muted-foreground">
            {part.feature_count} features · {part.characteristic_count} cotas
          </p>
        </div>
      </div>
      <CollapsibleSection
        title="Features"
        titleClassName="text-lg"
        icon={<Layers className="size-4 text-muted-foreground" />}
      >
        {editing && (
          <div className="max-w-md">
            <SearchSelect
              compact
              label="Añadir feature"
              placeholder="Añadir feature"
              emptyLabel="Seleccionar feature"
              options={(filters.data?.features ?? [])
                .filter(
                  (f) => !data.features.some((linked) => linked.id === f.id),
                )
                .map((f) => ({ value: f.id, label: f.name }))}
              disabled={membership.isPending}
              onChange={(featureId) => {
                if (featureId) membership.mutate({ featureId })
              }}
            />
          </div>
        )}
        {membership.error && (
          <p role="alert" className="text-sm text-destructive">
            {fileErrorMessage(membership.error)}
          </p>
        )}
        {data.features.map((feature) => (
          <FeatureCard
            key={feature.id}
            feature={feature}
            onSelect={() =>
              void navigate({
                to: "/features/$featureId",
                params: { featureId: feature.id },
              })
            }
            actions={
              editing ? (
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Desvincular ${feature.name}`}
                  disabled={membership.isPending}
                  onClick={() =>
                    membership.mutate({ featureId: feature.id, remove: true })
                  }
                >
                  <Trash2 className="size-4" />
                </Button>
              ) : undefined
            }
          />
        ))}
        {!data.features.length && (
          <p className="text-sm text-muted-foreground">
            Sin features vinculados.
          </p>
        )}
      </CollapsibleSection>
      <section
        id="cotas"
        className="scroll-mt-6"
        aria-label="Cotas de la pieza"
      >
        <CollapsibleSection
          title="Cotas"
          titleClassName="text-lg"
          icon={<Ruler className="size-4 text-muted-foreground" />}
          keepMounted
        >
          <MetrologyPage partId={part.id} search={search} embedded />
        </CollapsibleSection>
      </section>
      <CollapsibleSection
        title="Archivos"
        titleClassName="text-lg"
        icon={<Files className="size-4 text-muted-foreground" />}
      >
        {data.references.map(({ kind, file }) => {
          const Icon = ASSET_ICONS[kind]
          return (
            <div
              key={kind}
              className="flex items-center gap-2 rounded-md border px-2 py-1.5 text-sm"
            >
              <Icon className="size-4 shrink-0 text-muted-foreground" />
              <span className="w-16 shrink-0 text-xs uppercase text-muted-foreground">
                {ASSET_KIND_LABELS[kind]}
              </span>
              <Link
                to="/parts/$partId/fichero/$fileId"
                params={{ partId: part.id, fileId: file.id }}
                className="min-w-0 flex-1 truncate hover:underline"
              >
                {file.filename}
              </Link>
              <Button asChild size="icon" variant="ghost" className="size-7">
                <FileLink
                  fileId={file.id}
                  downloadFile
                  title={`Descargar ${file.filename}`}
                >
                  <Download className="size-3.5" />
                </FileLink>
              </Button>
            </div>
          )
        })}
        {!data.references.length && (
          <p className="text-sm text-muted-foreground">
            Sin archivos vinculados.
          </p>
        )}
      </CollapsibleSection>
    </div>
  )
}
