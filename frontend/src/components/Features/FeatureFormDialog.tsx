import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Lightbulb,
  Package2,
  Pencil,
  Plus,
  Trash2,
  TriangleAlert,
} from "lucide-react"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  type AssetKind,
  type FeatureAssetPublic,
  type FeatureCategory,
  type FeatureNotePublic,
  FeaturesService,
  type FilePublic,
  type NoteKind,
} from "@/client"
import { CollapsibleSection } from "@/components/Common/CollapsibleSection"
import { FileUpload } from "@/components/Common/FileUpload"
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
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { AssetDialog } from "./AssetDialog"
import {
  ASSET_ICONS,
  ASSET_KIND_LABELS,
  ASSET_KIND_SINGULAR,
  ASSET_KINDS,
  CATEGORIES,
  CATEGORY_LABELS,
  NOTE_KIND_SINGULAR,
} from "./constants"
import { NoteDialog } from "./NoteDialog"
import { PartSelect } from "./PartSelect"
import { featureParts } from "./parts"
import { featureQueryOptions } from "./queries"

const NO_CATEGORY = "none"

const formSchema = z.object({
  name: z.string().min(1, { message: "El nombre es obligatorio" }),
  description: z.string(),
  category: z.string(),
  tags: z.string(),
})

type FormData = z.infer<typeof formSchema>

const parseTags = (value: string) =>
  value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean)

function RowActions({
  onEdit,
  onDelete,
}: {
  onEdit: () => void
  onDelete: () => void
}) {
  return (
    <div className="ml-auto flex shrink-0 items-center">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="size-7"
        onClick={onEdit}
      >
        <Pencil className="size-3.5" />
        <span className="sr-only">Editar</span>
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="size-7 text-destructive"
        onClick={onDelete}
      >
        <Trash2 className="size-3.5" />
        <span className="sr-only">Borrar</span>
      </Button>
    </div>
  )
}

interface FeatureFormDialogProps {
  /** null = crear un feature nuevo. */
  featureId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

/**
 * Alta y edicion de un feature.
 *
 * Los datos basicos se guardan con el boton de abajo; los warnings, lessons
 * learned y piezas ejemplo se guardan al vuelo desde sus propias modales, por
 * lo que solo aparecen cuando el feature ya existe. Al crear uno nuevo la
 * modal se queda abierta en modo edicion para poder anadirlos sin salir.
 */
export function FeatureFormDialog({
  featureId,
  open,
  onOpenChange,
}: FeatureFormDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [createdId, setCreatedId] = useState<string | null>(null)
  const [image, setImage] = useState<FilePublic | null>(null)
  const [noteDialog, setNoteDialog] = useState<{
    kind: NoteKind
    note: FeatureNotePublic | null
  } | null>(null)
  const [assetDialog, setAssetDialog] = useState<{
    kind: AssetKind
    asset: FeatureAssetPublic | null
  } | null>(null)

  const activeId = featureId ?? createdId

  const { data: feature } = useQuery({
    ...featureQueryOptions(activeId ?? ""),
    enabled: open && Boolean(activeId),
  })

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    defaultValues: {
      name: "",
      description: "",
      category: NO_CATEGORY,
      tags: "",
    },
  })

  useEffect(() => {
    if (!open) {
      setCreatedId(null)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    if (!activeId) {
      form.reset({ name: "", description: "", category: NO_CATEGORY, tags: "" })
      setImage(null)
      return
    }
    if (feature) {
      form.reset({
        name: feature.name,
        description: feature.description ?? "",
        category: feature.category ?? NO_CATEGORY,
        tags: (feature.tags ?? []).join(", "),
      })
      setImage(feature.image ?? null)
    }
  }, [open, activeId, feature, form])

  const mutation = useMutation({
    mutationFn: (data: FormData) => {
      const body = {
        name: data.name,
        description: data.description || null,
        category:
          data.category === NO_CATEGORY
            ? null
            : (data.category as FeatureCategory),
        tags: parseTags(data.tags),
        image_id: image?.id ?? null,
      }
      return activeId
        ? FeaturesService.updateFeature({
            featureId: activeId,
            requestBody: body,
          })
        : FeaturesService.createFeature({ requestBody: body })
    },
    onSuccess: (saved) => {
      if (activeId) {
        showSuccessToast("Feature actualizado")
        onOpenChange(false)
      } else {
        // Se queda abierto para poder anadir warnings, lessons y adjuntos
        showSuccessToast("Feature creado: ya puedes anadirle contenido")
        setCreatedId(saved.id)
      }
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["features"] })
    },
  })

  const deleteNote = useMutation({
    mutationFn: (noteId: string) =>
      FeaturesService.deleteFeatureNote({ noteId }),
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["features"] })
    },
  })

  const deleteAsset = useMutation({
    mutationFn: (assetId: string) =>
      FeaturesService.deleteFeatureAsset({ assetId }),
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["features"] })
    },
  })

  const linkPart = useMutation({
    mutationFn: (partId: string) =>
      FeaturesService.linkFeaturePart({ featureId: activeId ?? "", partId }),
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["features"] })
    },
  })

  const unlinkPart = useMutation({
    mutationFn: (partId: string) =>
      FeaturesService.unlinkFeaturePart({ featureId: activeId ?? "", partId }),
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["features"] })
    },
  })

  const notesOf = (kind: NoteKind) =>
    (feature?.notes ?? []).filter((note) => note.kind === kind)
  const assetsOf = (kind: AssetKind) =>
    (feature?.assets ?? []).filter((asset) => asset.kind === kind)
  const parts = feature ? featureParts(feature) : []

  const noteSection = (kind: NoteKind, icon: React.ReactNode) => (
    <CollapsibleSection
      title={kind === "warning" ? "Warnings" : "Lessons Learned"}
      icon={icon}
    >
      {notesOf(kind).map((note) => (
        <div
          key={note.id}
          className="flex items-center gap-2 rounded-md border px-2 py-1 text-sm"
        >
          <span className="truncate">{note.title}</span>
          <RowActions
            onEdit={() => setNoteDialog({ kind, note })}
            onDelete={() => deleteNote.mutate(note.id)}
          />
        </div>
      ))}
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => setNoteDialog({ kind, note: null })}
      >
        <Plus className="mr-1 size-3.5" />
        Anadir {NOTE_KIND_SINGULAR[kind]}
      </Button>
    </CollapsibleSection>
  )

  // En edicion no se pinta descripcion (el titulo ya lo dice todo); Radix avisa
  // por consola si falta el DialogDescription y no se anula aria-describedby.
  const describedBy = activeId ? { "aria-describedby": undefined } : {}

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent
          className="max-h-[85vh] overflow-y-auto sm:max-w-2xl"
          {...describedBy}
        >
          <DialogHeader>
            <DialogTitle>
              {activeId ? "Editar feature" : "Nuevo feature"}
            </DialogTitle>
            {!activeId && (
              <DialogDescription>
                Guarda los datos basicos para poder anadirle warnings, lessons
                learned y piezas ejemplo.
              </DialogDescription>
            )}
          </DialogHeader>

          <Form {...form}>
            <form
              id="feature-form"
              onSubmit={form.handleSubmit((data) => mutation.mutate(data))}
            >
              <div className="flex gap-4">
                <div className="flex-1 space-y-4">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Nombre feature{" "}
                          <span className="text-destructive">*</span>
                        </FormLabel>
                        <FormControl>
                          <Input placeholder="Bolt Eye" {...field} />
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
                        <FormLabel>Descripcion</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="Que es y que agrupa"
                            className="min-h-20"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Imagen</Label>
                  <FileUpload
                    value={image}
                    onChange={setImage}
                    variant="image"
                    accept="image/*"
                  />
                </div>
              </div>

              <div className="grid gap-4 py-4 sm:grid-cols-3">
                <FormField
                  control={form.control}
                  name="category"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Categoria</FormLabel>
                      <Select
                        value={field.value}
                        onValueChange={field.onChange}
                      >
                        <FormControl>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Sin categoria" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value={NO_CATEGORY}>
                            Sin categoria
                          </SelectItem>
                          {CATEGORIES.map((category) => (
                            <SelectItem key={category} value={category}>
                              {CATEGORY_LABELS[category]}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="tags"
                  render={({ field }) => (
                    <FormItem className="sm:col-span-2">
                      <FormLabel>Tags</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="3212, N170, Bosch (separados por comas)"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </form>
          </Form>

          {activeId && (
            <div className="space-y-3">
              {noteSection(
                "warning",
                <TriangleAlert className="size-4 text-amber-500" />,
              )}
              {noteSection(
                "lesson",
                <Lightbulb className="size-4 text-yellow-500" />,
              )}
              <CollapsibleSection
                title="Piezas"
                icon={<Package2 className="size-4 text-muted-foreground" />}
              >
                {parts.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    Ninguna todavia. Anade una aqui para dejar constancia de que
                    el feature existe en esa pieza, aunque no subas ficheros.
                  </p>
                )}
                {parts.map((part) => {
                  const declared = (feature?.parts ?? []).some(
                    (item) => item.id === part.id,
                  )
                  const files = (feature?.assets ?? []).filter(
                    (asset) => asset.part?.id === part.id,
                  ).length
                  return (
                    <div
                      key={part.id}
                      className="flex items-center gap-2 rounded-md border px-2 py-1 text-sm"
                    >
                      <span className="font-mono font-semibold">
                        {part.code}
                      </span>
                      <span className="truncate text-muted-foreground">
                        {part.name}
                      </span>
                      <span className="ml-auto shrink-0 text-xs text-muted-foreground">
                        {files === 0
                          ? "sin ficheros"
                          : `${files} fichero${files === 1 ? "" : "s"}`}
                      </span>
                      {declared && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="size-7 shrink-0 text-destructive"
                          title="Quitar la pieza. Sus ficheros no se borran, y si los hay la pieza se sigue viendo."
                          onClick={() => unlinkPart.mutate(part.id)}
                        >
                          <Trash2 className="size-3.5" />
                          <span className="sr-only">Quitar {part.code}</span>
                        </Button>
                      )}
                    </div>
                  )
                })}
                <PartSelect
                  value={null}
                  onChange={(partId) => partId && linkPart.mutate(partId)}
                  placeholder="Anadir una pieza..."
                />
              </CollapsibleSection>

              <CollapsibleSection
                title="Ficheros por pieza"
                icon={<Package2 className="size-4 text-muted-foreground" />}
              >
                {ASSET_KINDS.map((kind) => {
                  const Icon = ASSET_ICONS[kind]
                  return (
                    <CollapsibleSection
                      key={kind}
                      title={ASSET_KIND_LABELS[kind]}
                    >
                      {assetsOf(kind).map((asset) => (
                        <div
                          key={asset.id}
                          className="flex items-center gap-2 rounded-md border px-2 py-1 text-sm"
                        >
                          <Icon className="size-3.5 shrink-0 text-muted-foreground" />
                          <span className="truncate">{asset.name}</span>
                          {asset.part && (
                            <span className="shrink-0 font-mono text-xs text-muted-foreground">
                              {asset.part.code}
                            </span>
                          )}
                          <RowActions
                            onEdit={() => setAssetDialog({ kind, asset })}
                            onDelete={() => deleteAsset.mutate(asset.id)}
                          />
                        </div>
                      ))}
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setAssetDialog({ kind, asset: null })}
                      >
                        <Plus className="mr-1 size-3.5" />
                        Anadir {ASSET_KIND_SINGULAR[kind]}
                      </Button>
                    </CollapsibleSection>
                  )
                })}
              </CollapsibleSection>
            </div>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={mutation.isPending}
            >
              {activeId ? "Cerrar" : "Cancelar"}
            </Button>
            <LoadingButton
              type="submit"
              form="feature-form"
              loading={mutation.isPending}
            >
              Guardar
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {activeId && noteDialog && (
        <NoteDialog
          featureId={activeId}
          kind={noteDialog.kind}
          note={noteDialog.note}
          open
          onOpenChange={(isOpen) => !isOpen && setNoteDialog(null)}
        />
      )}
      {activeId && assetDialog && (
        <AssetDialog
          featureId={activeId}
          kind={assetDialog.kind}
          asset={assetDialog.asset}
          open
          onOpenChange={(isOpen) => !isOpen && setAssetDialog(null)}
        />
      )}
    </>
  )
}
