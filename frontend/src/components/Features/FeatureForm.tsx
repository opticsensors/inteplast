import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Lightbulb, Package2, TriangleAlert } from "lucide-react"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  type FeatureCategory,
  FeaturesService,
  type FilePublic,
  type NoteKind,
} from "@/client"
import { CollapsibleSection } from "@/components/Common/CollapsibleSection"
import { FileUpload } from "@/components/Common/FileUpload"
import { Button } from "@/components/ui/button"
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
import { CATEGORIES, CATEGORY_LABELS } from "./constants"
import { NoteList } from "./NoteList"
import { PartAssetList } from "./PartAssetList"
import { PartSelect } from "./PartSelect"
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

interface FeatureFormProps {
  /** null = crear uno nuevo. */
  featureId: string | null
  /** Recien creado: la pagina lleva a su edicion para seguir rellenandolo. */
  onCreated: (featureId: string) => void
  onSaved: () => void
  onCancel: () => void
}

/**
 * Alta y edicion de un feature.
 *
 * Los datos basicos se guardan con el boton de abajo. Los warnings, lessons
 * learned y piezas ejemplo se guardan al vuelo desde sus propias modales, y
 * necesitan que el feature exista para colgarse de el: por eso al crear uno
 * nuevo solo salen los datos basicos, y las secciones aparecen despues.
 */
export function FeatureForm({
  featureId,
  onCreated,
  onSaved,
  onCancel,
}: FeatureFormProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [image, setImage] = useState<FilePublic | null>(null)

  const { data: feature } = useQuery({
    ...featureQueryOptions(featureId ?? ""),
    enabled: Boolean(featureId),
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
    if (!featureId) {
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
  }, [featureId, feature, form])

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
      return featureId
        ? FeaturesService.updateFeature({
            featureId,
            requestBody: body,
          })
        : FeaturesService.createFeature({ requestBody: body })
    },
    onSuccess: (saved) => {
      if (featureId) {
        showSuccessToast("Feature actualizado")
        onSaved()
      } else {
        showSuccessToast("Feature creado: ya puedes anadirle contenido")
        onCreated(saved.id)
      }
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["features"] })
    },
  })

  const linkPart = useMutation({
    mutationFn: (partId: string) =>
      FeaturesService.linkFeaturePart({ featureId: featureId ?? "", partId }),
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["features"] })
    },
  })

  const notesOf = (kind: NoteKind) =>
    (feature?.notes ?? []).filter((note) => note.kind === kind)

  // 🔑 Cada nota se escribe donde se lee: el titulo en su sitio y el cuerpo
  // dentro del desplegable. Ni boton de editar ni modal.
  const noteSection = (kind: NoteKind, icon: React.ReactNode) => (
    <CollapsibleSection
      title={kind === "warning" ? "Warnings" : "Lessons Learned"}
      icon={icon}
    >
      <NoteList featureId={featureId ?? ""} kind={kind} notes={notesOf(kind)} />
    </CollapsibleSection>
  )

  return (
    <div className="flex flex-col gap-6">
      {/* Los botones ocupan el mismo sitio que *Editar* y *Borrar* en modo
            lectura, y estan junto a lo unico que hay que guardar a mano: las
            secciones de abajo se guardan solas. */}
      <div className="flex items-center justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onCancel}
          disabled={mutation.isPending}
        >
          Cancelar
        </Button>
        <LoadingButton
          type="submit"
          form="feature-form"
          size="sm"
          loading={mutation.isPending}
        >
          Guardar
        </LoadingButton>
      </div>

      <Form {...form}>
        <form
          id="feature-form"
          onSubmit={form.handleSubmit((data) => mutation.mutate(data))}
        >
          {/* Misma cabecera que la ficha —foto a la izquierda, identidad a
                la derecha— con las casillas en el sitio de cada dato. */}
          <div className="flex gap-4 rounded-lg border p-4 sm:gap-6 sm:p-6">
            <FileUpload
              value={image}
              onChange={setImage}
              variant="image"
              accept="image/*"
              className="shrink-0"
              boxClassName="size-32 sm:size-48"
            />

            <div className="min-w-0 flex-1 space-y-3">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="sr-only">Nombre feature</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Nombre del feature"
                        className="h-auto py-1 text-2xl font-bold tracking-tight md:text-2xl"
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
                    <FormLabel className="sr-only">Descripcion</FormLabel>
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

              <div className="grid gap-3 sm:grid-cols-3">
                <FormField
                  control={form.control}
                  name="category"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Categoria</FormLabel>
                      {/* 🔴 Radix dispara `onValueChange("")` el solo cuando el
                        Select vive dentro de un <form> y su lista todavia no
                        se ha abierto: borraba la categoria y el PUT se iba con
                        `category: ""` -> 422. Un cambio de verdad nunca trae
                        cadena vacia (el «Sin categoria» vale "none"). */}
                      <Select
                        value={field.value}
                        onValueChange={(next) => next && field.onChange(next)}
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
            </div>
          </div>
        </form>
      </Form>

      {featureId && (
        <div className="space-y-4">
          {noteSection(
            "warning",
            <TriangleAlert className="size-4 text-amber-500" />,
          )}
          {noteSection(
            "lesson",
            <Lightbulb className="size-4 text-yellow-500" />,
          )}
          <CollapsibleSection
            title="Piezas ejemplo"
            icon={<Package2 className="size-4 text-muted-foreground" />}
          >
            {/* 🔑 El MISMO componente que la ficha, en modo edicion. Antes
                  aqui se agrupaba por tipo y en la ficha por pieza: dos
                  idiomas distintos para lo mismo. */}
            {feature && (
              <PartAssetList
                feature={feature}
                editable
                footer={
                  <PartSelect
                    value={null}
                    onChange={(partId) => partId && linkPart.mutate(partId)}
                    placeholder="Anadir una pieza..."
                  />
                }
              />
            )}
          </CollapsibleSection>
        </div>
      )}
    </div>
  )
}
