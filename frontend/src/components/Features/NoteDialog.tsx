import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Lightbulb, TriangleAlert } from "lucide-react"
import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  type FeatureNotePublic,
  FeaturesService,
  type NoteKind,
} from "@/client"
import { RichTextEditor } from "@/components/Common/RichText"
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
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { NOTE_KIND_SINGULAR } from "./constants"

const formSchema = z.object({
  title: z.string().min(1, { message: "El titulo es obligatorio" }),
  body: z.string(),
})

type FormData = z.infer<typeof formSchema>

interface NoteDialogProps {
  featureId: string
  kind: NoteKind
  /** null = crear; con nota = editar. */
  note: FeatureNotePublic | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

/** Alta y edicion de una advertencia o leccion aprendida. */
export function NoteDialog({
  featureId,
  kind,
  note,
  open,
  onOpenChange,
}: NoteDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    defaultValues: { title: "", body: "" },
  })

  useEffect(() => {
    if (open) {
      form.reset({ title: note?.title ?? "", body: note?.body ?? "" })
    }
  }, [open, note, form])

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      note
        ? FeaturesService.updateFeatureNote({
            noteId: note.id,
            requestBody: data,
          })
        : FeaturesService.createFeatureNote({
            featureId,
            requestBody: { ...data, kind },
          }),
    onSuccess: () => {
      showSuccessToast(note ? "Nota actualizada" : "Nota anadida")
      onOpenChange(false)
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["features"] })
    },
  })

  const Icon = kind === "warning" ? TriangleAlert : Lightbulb

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Icon className="size-4 text-amber-500" />
            {note ? "Editar" : "Anadir"} {NOTE_KIND_SINGULAR[kind]}
          </DialogTitle>
          <DialogDescription>
            El texto admite **negrita**, *cursiva*, `codigo` y listas con guion.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit((data) => mutation.mutate(data))}>
            <div className="grid gap-4 py-2">
              <FormField
                control={form.control}
                name="title"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Titulo <span className="text-destructive">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input placeholder="Introduce un titulo" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="body"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Detalles</FormLabel>
                    <FormControl>
                      <RichTextEditor
                        value={field.value}
                        onChange={field.onChange}
                        placeholder="Anadir detalles..."
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={mutation.isPending}
              >
                Cancelar
              </Button>
              <LoadingButton type="submit" loading={mutation.isPending}>
                {note ? "Guardar" : "Anadir"}
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
