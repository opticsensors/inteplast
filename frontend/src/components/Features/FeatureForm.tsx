import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useBlocker } from "@tanstack/react-router"
import { Lightbulb, Package2, TriangleAlert } from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  ApiError,
  FeaturesService,
  type FilePublic,
  type NoteKind,
} from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { Textarea } from "@/components/ui/textarea"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { type CoverDraft, withDrafts } from "./coverSlides"
import {
  EditingSessionContext,
  useEditingSession,
  useNewEditingSession,
} from "./EditingSession"
import { FeatureCoverEditor } from "./FeatureCoverEditor"
import {
  FEATURE_COLUMNS,
  FeatureBreadcrumb,
  FeatureSection,
} from "./FeatureLayout"
import { NoteList } from "./NoteList"
import { PartAssetList } from "./PartAssetList"
import { featureParts } from "./parts"
import { PartUnlinkedContext } from "./partUnlinked"
import { featureQueryOptions } from "./queries"

const formSchema = z.object({
  name: z.string().min(1, { message: "El nombre es obligatorio" }),
  description: z.string(),
})

type FormData = z.infer<typeof formSchema>

interface FeatureFormProps {
  /** null = crear uno nuevo. */
  featureId: string | null
  /** Alta terminada: abrir la ficha creada. */
  onCreated: (featureId: string) => void
  onSaved: () => void
  onCancel: () => void
}

/**
 * Alta y edicion de un feature.
 *
 * Todas las secciones estan disponibles desde el alta. El primer contenido
 * crea el feature automaticamente; abrir el formulario vacio no crea registros.
 */
export function FeatureForm(props: FeatureFormProps) {
  const session = useNewEditingSession()
  return (
    <EditingSessionContext.Provider value={session}>
      <FeatureFormContent {...props} />
    </EditingSessionContext.Provider>
  )
}

function FeatureFormContent({
  featureId: initialFeatureId,
  onCreated,
  onSaved,
  onCancel,
}: FeatureFormProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [createdFeatureId, setCreatedFeatureId] = useState<string | null>(null)
  const featureId = initialFeatureId ?? createdFeatureId
  const featureIdRef = useRef(initialFeatureId)
  const creation = useRef<Promise<string> | null>(null)
  // Image of the feature itself (shown only while it has no pieces) and the
  // covers edited on each piece; all of them are saved with «Guardar».
  const [image, setImage] = useState<FilePublic | null>(null)
  const [imageDirty, setImageDirty] = useState(false)
  const imageDraft = useRef<{ image: FilePublic | null; dirty: boolean }>({
    image: null,
    dirty: false,
  })
  const [partDrafts, setPartDrafts] = useState<ReadonlyMap<string, CoverDraft>>(
    new Map(),
  )
  const partDraftsRef = useRef(partDrafts)
  partDraftsRef.current = partDrafts
  // Only after the server confirms the unlink: a failed one keeps the draft.
  const dropPartDraft = useCallback((partId: string) => {
    setPartDrafts((drafts) => {
      if (!drafts.has(partId)) return drafts
      const rest = new Map(drafts)
      rest.delete(partId)
      partDraftsRef.current = rest
      return rest
    })
  }, [])
  const bypassNavigation = useRef(false)
  const session = useEditingSession()!

  const { data: feature } = useQuery({
    ...featureQueryOptions(featureId ?? ""),
    enabled: Boolean(featureId),
  })
  const slides = useMemo(
    () => (feature ? withDrafts(feature, partDrafts) : []),
    [feature, partDrafts],
  )

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    defaultValues: {
      name: "",
      description: "",
    },
  })

  // Notes and parts may be added concurrently: they share a single creation.
  const ensureFeatureId = async (): Promise<string> => {
    if (initialFeatureId) return initialFeatureId
    if (featureIdRef.current) return featureIdRef.current
    if (!creation.current) {
      const values = form.getValues()
      creation.current = FeaturesService.createFeature({
        requestBody: {
          name: values.name.trim() || "Nuevo feature",
          description: values.description || null,
          image_id: imageDraft.current.image?.id ?? null,
        },
      })
        .then((created) => {
          featureIdRef.current = created.id
          queryClient.setQueryData(
            featureQueryOptions(created.id).queryKey,
            created,
          )
          setCreatedFeatureId(created.id)
          return created.id
        })
        .finally(() => {
          creation.current = null
        })
    }
    return creation.current
  }

  // Subscribe to dirtyFields so background refreshes retain edited fields.
  const { dirtyFields, isDirty } = form.formState
  const headerDirty = useRef(false)
  headerDirty.current = isDirty || imageDirty || partDrafts.size > 0

  const blocker = useBlocker({
    shouldBlockFn: async () => {
      if (bypassNavigation.current) return false
      const saved = await session.flush()
      return !saved || headerDirty.current
    },
    enableBeforeUnload: () => headerDirty.current || session.pending(),
    withResolver: true,
  })

  useEffect(() => {
    if (!featureId) {
      return
    }
    if (feature) {
      form.reset(
        {
          name: feature.name,
          description: feature.description ?? "",
        },
        { keepDirtyValues: true },
      )
      if (!imageDirty) {
        imageDraft.current = { image: feature.image ?? null, dirty: false }
        setImage(feature.image ?? null)
      }
    }
  }, [featureId, feature, form, imageDirty])

  const checkDraftParts = async (savedId: string) => {
    if (!partDraftsRef.current.size) return
    const latest = await queryClient.fetchQuery({
      ...featureQueryOptions(savedId),
      staleTime: 0,
    })
    const present = new Set(featureParts(latest).map((part) => part.id))
    const gone = [...partDraftsRef.current].filter(([id]) => !present.has(id))
    if (!gone.length) return

    const rest = new Map(partDraftsRef.current)
    for (const [partId] of gone) rest.delete(partId)
    partDraftsRef.current = rest
    setPartDrafts(rest)
    const names = gone.map(([, draft]) => draft.partCode)
    const removed =
      names.length === 1
        ? `La pieza ${names[0]} ya no está en este feature. Se ha descartado su borrador de portada.`
        : `Las piezas ${names.join(", ")} ya no están en este feature. Se han descartado sus borradores de portada.`
    throw new Error(
      `${removed} No se ha guardado nada. Revisa la ficha y vuelve a guardar.`,
    )
  }

  const mutation = useMutation({
    mutationFn: async (data: FormData) => {
      if (!(await session.flush()))
        throw new Error(
          "Hay cambios sin guardar en las notas, piezas o ficheros",
        )
      const body = {
        name: data.name,
        description: data.description || null,
        image_id: imageDraft.current.image?.id ?? null,
      }
      const savedId = initialFeatureId ?? featureIdRef.current
      if (savedId) await checkDraftParts(savedId)
      // Header and covers go in one request: the server saves all or nothing.
      const covers = [...partDraftsRef.current].map(([partId, draft]) => ({
        part_id: partId,
        image_id: draft.image?.id ?? null,
        cover_3d: draft.image ? draft.cover : null,
      }))
      const saved = savedId
        ? await FeaturesService.updateFeature({
            featureId: savedId,
            requestBody: {
              ...(dirtyFields.name ? { name: body.name } : {}),
              ...(dirtyFields.description
                ? { description: body.description }
                : {}),
              ...(imageDraft.current.dirty ? { image_id: body.image_id } : {}),
              ...(covers.length ? { part_covers: covers } : {}),
            },
          }).catch(async (error: unknown) => {
            // A piece can also be unlinked between the pre-save read and the PUT.
            if (
              error instanceof ApiError &&
              error.status === 409 &&
              covers.length
            )
              await checkDraftParts(savedId)
            throw error
          })
        : { id: await ensureFeatureId() }
      partDraftsRef.current = new Map()
      setPartDrafts(partDraftsRef.current)
      return saved
    },
    onSuccess: () => {
      if (initialFeatureId) {
        showSuccessToast("Feature actualizado")
      } else {
        showSuccessToast("Feature creado")
      }
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["features"] })
    },
  })

  const submit = async (data: FormData, proceed?: () => void) => {
    try {
      const saved = await mutation.mutateAsync(data)
      form.reset(data)
      imageDraft.current.dirty = false
      setImageDirty(false)
      bypassNavigation.current = true
      if (proceed) proceed()
      else if (initialFeatureId) onSaved()
      else onCreated(saved.id)
    } catch {
      /* The editor and its failed drafts stay mounted for retry. */
    }
  }

  const cancel = async () => {
    if (!(await session.flush())) {
      showErrorToast(
        "Hay cambios sin guardar. Corrige los campos o reintenta antes de salir.",
      )
      return
    }
    bypassNavigation.current = true
    onCancel()
  }

  const notesOf = (kind: NoteKind) =>
    (feature?.notes ?? []).filter((note) => note.kind === kind)

  // 🔑 Cada nota se escribe donde se lee: el titulo en su sitio y el cuerpo
  // dentro del desplegable. Ni boton de editar ni modal.
  const noteSection = (kind: NoteKind, icon: React.ReactNode) => (
    <FeatureSection
      title={kind === "warning" ? "Advertencias" : "Lecciones aprendidas"}
      count={notesOf(kind).length}
      icon={icon}
    >
      <div className="space-y-2">
        <NoteList
          featureId={featureId ?? ""}
          ensureFeatureId={ensureFeatureId}
          kind={kind}
          notes={notesOf(kind)}
        />
      </div>
    </FeatureSection>
  )

  return (
    <PartUnlinkedContext.Provider value={dropPartDraft}>
      <fieldset
        disabled={mutation.isPending}
        className="flex min-w-0 flex-col gap-5"
      >
        {/* Los botones ocupan el mismo sitio que *Editar* y *Borrar* en modo
            lectura, y estan junto a lo unico que hay que guardar a mano: las
            secciones de abajo se guardan solas. */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <FeatureBreadcrumb name={feature?.name ?? "Nuevo feature"} />
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                void cancel()
              }}
              disabled={mutation.isPending}
            >
              Cancelar
            </Button>
            <LoadingButton
              type="submit"
              form="feature-form"
              loading={mutation.isPending}
            >
              {initialFeatureId ? "Guardar cambios" : "Guardar"}
            </LoadingButton>
          </div>
        </div>

        <Form {...form}>
          <form
            id="feature-form"
            onSubmit={form.handleSubmit((data) => submit(data))}
          >
            {/* Misma cabecera que la ficha —foto a la izquierda, identidad a
                la derecha— con las casillas en el sitio de cada dato. */}
            <div className="flex flex-col gap-4 rounded-lg border bg-card p-4 sm:flex-row sm:gap-6 sm:p-5">
              <FeatureCoverEditor
                feature={feature}
                slides={slides}
                image={image}
                onImageChange={(file) => {
                  imageDraft.current = { image: file, dirty: true }
                  setImage(file)
                  setImageDirty(true)
                }}
                onPartChange={(partId, draft) =>
                  setPartDrafts((drafts) => new Map(drafts).set(partId, draft))
                }
              />

              <div className="min-w-0 flex-1 space-y-3">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Nombre</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Nombre del feature"
                          className="text-lg md:text-lg"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="description"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Descripción</FormLabel>
                      <FormControl>
                        <Textarea
                          placeholder="Que es y que agrupa"
                          className="min-h-16"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>
          </form>
        </Form>

        <div className={FEATURE_COLUMNS}>
          <div className="min-w-0 space-y-5">
            {noteSection(
              "warning",
              <TriangleAlert className="size-5 shrink-0 text-amber-500" />,
            )}
            {noteSection(
              "lesson",
              <Lightbulb className="size-5 shrink-0 text-amber-500" />,
            )}
          </div>
          <div id="example-parts-editor" className="min-w-0 scroll-mt-20">
            <FeatureSection
              title="Piezas ejemplo"
              count={feature ? featureParts(feature).length : 0}
              icon={
                <Package2 className="size-5 shrink-0 text-muted-foreground" />
              }
            >
              {/* 🔑 El MISMO componente que la ficha, en modo edicion. Antes
                  aqui se agrupaba por tipo y en la ficha por pieza: dos
                  idiomas distintos para lo mismo. */}
              <PartAssetList
                feature={
                  feature ?? {
                    id: featureId ?? "",
                    name: "Nuevo feature",
                    notes: [],
                    assets: [],
                    parts: [],
                  }
                }
                ensureFeatureId={ensureFeatureId}
                editable
              />
            </FeatureSection>
          </div>
        </div>
        <Dialog
          open={blocker.status === "blocked"}
          onOpenChange={(open) => {
            if (!open) blocker.reset?.()
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Cambios sin guardar</DialogTitle>
              <DialogDescription>
                Guarda los cambios antes de salir. Si falla el guardado, tus
                cambios se mantienen en esta ficha para reintentarlo.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => blocker.reset?.()}
              >
                Seguir editando
              </Button>
              <LoadingButton
                loading={mutation.isPending}
                onClick={form.handleSubmit((data) =>
                  submit(data, blocker.proceed),
                )}
              >
                Guardar y salir
              </LoadingButton>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </fieldset>
    </PartUnlinkedContext.Provider>
  )
}
