import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { Lightbulb, Package2, TriangleAlert } from "lucide-react"

import { ApiError, type NoteKind } from "@/client"
import { CollapsibleSection } from "@/components/Common/CollapsibleSection"
import { RichTextView } from "@/components/Common/RichText"
import { CATEGORY_LABELS } from "@/components/Features/constants"
import DeleteFeature from "@/components/Features/DeleteFeature"
import { FeatureActions } from "@/components/Features/FeatureActions"
import { FeatureCover } from "@/components/Features/FeatureCover"
import { FeatureForm } from "@/components/Features/FeatureForm"
import { FeatureNotFound } from "@/components/Features/FeatureNotFound"
import { PartAssetList } from "@/components/Features/PartAssetList"
import { featureParts } from "@/components/Features/parts"
import { featureQueryOptions } from "@/components/Features/queries"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import useAuth from "@/hooks/useAuth"

const flag = (value: unknown) => value === true || value === "true"

export const Route = createFileRoute("/_layout/features_/$featureId")({
  component: FeatureDetail,
  // Opcionales a proposito: el catalogo enlaza la ficha sin pasar nada, y
  // TanStack obliga a pasar en cada enlace todo lo que el validador declare.
  validateSearch: (search: Record<string, unknown>): { editar?: true } => ({
    ...(flag(search.editar) ? { editar: true as const } : {}),
  }),
  head: () => ({
    meta: [
      {
        title: "Feature - INTEPLAST",
      },
    ],
  }),
})

/** Un feature borrado o un id inventado no van a existir por reintentarlo. */
const isNotFound = (error: Error) =>
  error instanceof ApiError && error.status === 404

/**
 * La ficha del feature. Una sola pagina con dos caras, marcadas en la URL:
 *
 * | URL | Cara |
 * |---|---|
 * | `/features/{id}` | lectura, con acceso directo a editar |
 * | `?editar=true` | **el mismo contenido, editable aqui mismo** |
 *
 * Editar no cambia el reparto de la pagina: cada dato pasa a ser su casilla en
 * el sitio donde estaba. El modo vive en la URL y no en un `useState` para que
 * el boton *Editar* de la lista pueda entrar directo, y para que recargar no
 * te eche del modo edicion.
 */
function FeatureDetail() {
  const { featureId } = Route.useParams()
  const { editar } = Route.useSearch()
  const navigate = useNavigate()
  const { user } = useAuth()

  // Cambiar de modo no añade pasos al historial: atras vuelve al catalogo
  // con sus filtros, tanto al editar desde la tarjeta como desde la ficha.
  const setEditing = (editing: boolean) =>
    navigate({
      to: "/features/$featureId",
      params: { featureId },
      search: editing ? { editar: true } : {},
      replace: true,
      resetScroll: false,
    })
  const toRead = () => setEditing(false)

  const {
    data: feature,
    isPending,
    isError,
  } = useQuery({
    ...featureQueryOptions(featureId),
    retry: (failureCount, error) => !isNotFound(error) && failureCount < 3,
  })

  const notesOf = (kind: NoteKind) =>
    (feature?.notes ?? []).filter((note) => note.kind === kind)

  if (isPending) {
    return (
      <div className="flex flex-col gap-6">
        <div className="flex gap-4 rounded-lg border p-4 sm:gap-6 sm:p-6">
          <Skeleton className="size-32 shrink-0 sm:size-48" />
          <div className="flex-1 space-y-3">
            <Skeleton className="h-8 w-1/2" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-6 w-40" />
          </div>
        </div>
        <div className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      </div>
    )
  }

  if (isError || !feature) return <FeatureNotFound />

  // Editando: la MISMA pagina y el MISMO reparto —foto a la izquierda, datos
  // a la derecha, secciones debajo—, solo que cada dato es ahora su casilla.
  if (editar) {
    return (
      <FeatureForm
        key={feature.id}
        featureId={feature.id}
        onCreated={() => undefined}
        onSaved={toRead}
        onCancel={toRead}
      />
    )
  }

  const parts = featureParts(feature)
  const tags = feature.tags ?? []

  return (
    <div className="flex flex-col gap-6">
      <div className="flex justify-end gap-2">
        {(user?.is_superuser || user?.id === feature.owner_id) && (
          <DeleteFeature
            featureId={feature.id}
            featureName={feature.name}
            onSuccess={() => navigate({ to: "/features", replace: true })}
          />
        )}
        <FeatureActions onEdit={() => setEditing(true)} variant="outline" />
      </div>
      {/* Identidad del feature: la misma lectura que la tarjeta del buscador
          —imagen a la izquierda, todo lo que dice QUE es a la derecha— pero a
          tamaño de pagina. Lo que hay que saber para diseñar va debajo. */}
      <div className="flex gap-4 rounded-lg border p-4 sm:gap-6 sm:p-6">
        <FeatureCover key={feature.id} feature={feature} />

        <div className="min-w-0 flex-1 space-y-3">
          <div className="space-y-1">
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
              {feature.name}
            </h1>
            {feature.description && (
              <p className="text-muted-foreground">{feature.description}</p>
            )}
          </div>

          {(feature.category || tags.length > 0) && (
            <div className="flex flex-wrap gap-1">
              {feature.category && (
                <Badge variant="secondary">
                  {CATEGORY_LABELS[feature.category]}
                </Badge>
              )}
              {tags.map((tag) => (
                <Badge key={tag} variant="outline">
                  {tag}
                </Badge>
              ))}
            </div>
          )}

          {parts.length > 0 && (
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
              <Package2 className="size-4 shrink-0" />
              <span>
                {parts.length} pieza{parts.length === 1 ? "" : "s"}
              </span>
              <span aria-hidden>·</span>
              {parts.map((part, index) => (
                <span key={part.id}>
                  <Link
                    to="/parts/$partId"
                    params={{ partId: part.id }}
                    className="hover:underline"
                  >
                    <span className="font-mono text-foreground">
                      {part.code}
                    </span>
                    {part.name && ` ${part.name}`}
                  </Link>
                  {index < parts.length - 1 && ","}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="space-y-4">
        <CollapsibleSection
          title="Warnings"
          titleClassName="text-lg"
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
          titleClassName="text-lg"
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
          titleClassName="text-lg"
          icon={<Package2 className="size-4 text-muted-foreground" />}
        >
          <PartAssetList feature={feature} />
        </CollapsibleSection>
      </div>
    </div>
  )
}
