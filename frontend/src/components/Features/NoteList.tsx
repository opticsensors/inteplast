import { useMutation, useQueryClient } from "@tanstack/react-query"
import { ChevronDown, Plus, Trash2 } from "lucide-react"
import { type ReactNode, useEffect, useMemo, useRef, useState } from "react"

import {
  type FeatureNotePublic,
  type FeatureNoteUpdate,
  FeaturesService,
  type NoteKind,
} from "@/client"
import { RichTextEditor } from "@/components/Common/RichText"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"
import { handleError } from "@/utils"
import { NOTE_KIND_SINGULAR } from "./constants"
import { SaveStatus } from "./SaveStatus"
import { SortableEditorList } from "./SortableEditorList"
import { useAutosave } from "./useAutosave"
import { usePendingTask } from "./usePendingTask"

/** Lo que se escribe al crearla: se selecciona solo para escribir encima. */
const NEW_TITLE: Record<NoteKind, string> = {
  warning: "Nueva advertencia",
  lesson: "Nueva leccion aprendida",
}

/**
 * Una nota en modo edicion: **el titulo se escribe encima** y el desplegable
 * abre el cuerpo, tambien editable ahi mismo.
 *
 * 🔑 No hay boton de editar ni modal: se escribe donde se lee. Y no hay boton
 * de guardar —se guarda solo, 0,7 s despues de la ultima tecla— porque las
 * notas siempre se han guardado por su cuenta, aparte de la cabecera.
 */
function NoteRow({
  note,
  isNew,
  dragHandle,
}: {
  note: FeatureNotePublic
  /** Recien creada: se abre y se selecciona el titulo de oficio. */
  isNew: boolean
  dragHandle: ReactNode
}) {
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()
  const [isOpen, setIsOpen] = useState(isNew)
  const titleRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isNew) titleRef.current?.select()
  }, [isNew])

  const update = useMutation({
    mutationFn: (data: FeatureNoteUpdate) =>
      FeaturesService.updateFeatureNote({ noteId: note.id, requestBody: data }),
    onError: handleError.bind(showErrorToast),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["features"] }),
  })

  const server = useMemo(
    () => ({ title: note.title, body: note.body ?? "" }),
    [note.title, note.body],
  )
  const autosave = useAutosave(
    server,
    (patch) => update.mutateAsync(patch),
    (values) => Boolean(values.title.trim()),
  )
  const { title, body } = autosave.values

  const remove = useMutation({
    mutationFn: () => FeaturesService.deleteFeatureNote({ noteId: note.id }),
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["features"] })
    },
  })

  return (
    <div className="rounded-md border">
      <div className="flex items-center gap-1 px-1 py-1">
        {dragHandle}
        <button
          type="button"
          onClick={() => setIsOpen((open) => !open)}
          className="shrink-0 rounded p-1 hover:bg-accent"
          title={isOpen ? "Contraer" : "Ver y editar los detalles"}
        >
          <ChevronDown
            className={cn(
              "size-4 text-muted-foreground transition-transform",
              !isOpen && "-rotate-90",
            )}
          />
          <span className="sr-only">Desplegar {note.title}</span>
        </button>
        <Input
          ref={titleRef}
          value={title}
          onChange={(event) => autosave.change({ title: event.target.value })}
          placeholder="Titulo de la nota"
          className={cn(
            "h-8 border-0 px-2 text-sm font-medium shadow-none focus-visible:ring-1",
            !title.trim() && "ring-1 ring-destructive",
          )}
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="size-7 shrink-0 text-destructive"
          onClick={() => remove.mutate()}
          disabled={remove.isPending}
        >
          <Trash2 className="size-3.5" />
          <span className="sr-only">Borrar {note.title}</span>
        </Button>
      </div>

      {isOpen && (
        <div className="px-2 pb-2">
          <RichTextEditor
            value={body}
            onChange={(body) => autosave.change({ body })}
            placeholder="Detalles: **negrita**, *cursiva*, `codigo` y listas con guion"
          />
        </div>
      )}
      <SaveStatus
        error={autosave.error}
        saving={autosave.saving}
        retry={autosave.flush}
      />
    </div>
  )
}

/**
 * Las notas de un tipo (warnings o lessons learned) en modo edicion.
 *
 * *Anadir* la crea en el momento y la deja abierta con el titulo seleccionado,
 * en vez de abrir una modal que hay que rellenar y confirmar.
 */
export function NoteList({
  featureId,
  ensureFeatureId,
  kind,
  notes,
}: {
  featureId: string
  ensureFeatureId?: () => Promise<string>
  kind: NoteKind
  notes: FeatureNotePublic[]
}) {
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()
  const [newNoteId, setNewNoteId] = useState<string | null>(null)

  const create = useMutation({
    mutationFn: async () =>
      FeaturesService.createFeatureNote({
        featureId: ensureFeatureId ? await ensureFeatureId() : featureId,
        requestBody: {
          kind,
          title: NEW_TITLE[kind],
          body: "",
          // Al final de la lista: el backend ordena por `position`.
          position:
            Math.max(-1, ...notes.map((note) => note.position ?? 0)) + 1,
        },
      }),
    onSuccess: (created) => setNewNoteId(created.id),
    onError: handleError.bind(showErrorToast),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["features"] }),
  })
  const creating = usePendingTask((_: undefined) => create.mutateAsync())

  return (
    <>
      <SortableEditorList
        items={[...notes].sort((a, b) => (a.position ?? 0) - (b.position ?? 0))}
        saveOrder={(ids) =>
          FeaturesService.reorderFeatureNotes({
            featureId,
            requestBody: { kind, note_ids: ids },
          })
        }
        dragLabel={(note) => `Mover ${NOTE_KIND_SINGULAR[kind]} ${note.title}`}
      >
        {(note, handle) => (
          <NoteRow
            note={note}
            isNew={note.id === newNoteId}
            dragHandle={handle}
          />
        )}
      </SortableEditorList>
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => void creating.run(undefined)}
        disabled={creating.pending}
      >
        <Plus className="mr-1 size-3.5" />
        Anadir {NOTE_KIND_SINGULAR[kind]}
      </Button>
      <SaveStatus
        error={creating.error}
        saving={creating.pending}
        retry={creating.retry}
      />
    </>
  )
}
