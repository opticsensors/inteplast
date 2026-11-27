import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { FileSpreadsheet, Layers, Loader2, Plus, Trash2 } from "lucide-react"
import { type ReactNode, useState } from "react"
import { type ComponentDefinition, PartsService } from "@/client"
import { SearchField } from "@/components/Common/SearchField"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import {
  fileStem,
  proposedComponent,
  proposesWholeFile,
} from "./componentProposals"
import { FILE_ICONS, FILE_LABELS } from "./pieceFileDrafts"

const UNASSIGNED = "__unassigned"

type Owner = { key?: string; proposed: boolean }

function componentKey(name: string) {
  return name
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toUpperCase()
    .replace(/[^A-Z0-9_-]/g, "_")
    .slice(0, 24)
}

/**
 * Componentes de una pieza de conjunto. Sin componentes la pieza se lee como una sola.
 *
 * Los archivos y hojas sin asignación guardada reciben una propuesta por el nombre de
 * cada componente. Lo que se guarda asignado, o sin asignar, prevalece.
 */
export function PartComponents({
  partId,
  defaultOpen = false,
  onClosed,
}: {
  partId: string
  defaultOpen?: boolean
  /** Al cerrar el diálogo, guardado o no. */
  onClosed?: (saved: boolean) => void
}) {
  const [open, setOpen] = useState(defaultOpen)
  const [draft, setDraft] = useState<ComponentDefinition[] | null>(null)
  // Fuentes que el usuario deja sin asignar: se guardan y no se vuelven a proponer.
  const [clearedDraft, setCleared] = useState<Set<string> | null>(null)
  const [search, setSearch] = useState("")
  const client = useQueryClient()
  const query = useQuery({
    queryKey: ["part-components", partId],
    queryFn: () => PartsService.readComponentOptions({ partId }),
    enabled: open,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  })
  const components = draft ?? query.data?.components ?? []
  const cleared = clearedDraft ?? new Set(query.data?.unassigned ?? [])
  const named = components.filter((c) => c.name.trim())
  const update = (index: number, values: Partial<ComponentDefinition>) =>
    setDraft(components.map((c, i) => (i === index ? { ...c, ...values } : c)))
  const fileOwner = (path: string): Owner => {
    const saved = components.find((c) => c.files?.some((f) => f.path === path))
    if (saved) return { key: saved.key, proposed: false }
    if (cleared.has(`file:${path}`) || !proposesWholeFile(path))
      return { proposed: false }
    const key = proposedComponent(fileStem(path), named)
    return { key, proposed: Boolean(key) }
  }
  const sheetOwner = (sheet: string): Owner => {
    const saved = components.find((c) => c.sheets?.includes(sheet))
    if (saved) return { key: saved.key, proposed: false }
    if (cleared.has(`sheet:${sheet}`)) return { proposed: false }
    const key = proposedComponent(sheet, named)
    return { key, proposed: Boolean(key) }
  }
  const allSources = query.data?.sources ?? []
  const allSheets = query.data?.sheet_names ?? []
  const proposals =
    allSources.some((s) => fileOwner(s.path).proposed) ||
    allSheets.some((sheet) => sheetOwner(sheet).proposed)
  /** La organización que se guarda: lo asignado más lo propuesto. */
  const organization = () =>
    components.map((c) => ({
      ...c,
      files: [
        ...(c.files ?? []),
        ...allSources
          .filter((s) => {
            const owner = fileOwner(s.path)
            return owner.proposed && owner.key === c.key
          })
          .map((s) => ({ path: s.path, revision: "" })),
      ],
      sheets: [
        ...(c.sheets ?? []),
        ...allSheets.filter((sheet) => {
          const owner = sheetOwner(sheet)
          return owner.proposed && owner.key === c.key
        }),
      ],
    }))
  /**
   * Lo que se guarda sin componente queda decidido, se haya tocado su selector o se
   * viera así por no coincidir o ser ambiguo: no se vuelve a proponer. Los archivos y
   * hojas que aparezcan después sí reciben propuesta.
   */
  const unassigned = () =>
    [
      ...new Set([
        ...cleared,
        ...allSources
          .filter((s) => !fileOwner(s.path).key)
          .map((s) => `file:${s.path}`),
        ...allSheets
          .filter((sheet) => !sheetOwner(sheet).key)
          .map((sheet) => `sheet:${sheet}`),
      ]),
    ].sort()
  const assignFile = (path: string, key: string, revision = "") => {
    const next = new Set(cleared)
    if (key === UNASSIGNED) next.add(`file:${path}`)
    else next.delete(`file:${path}`)
    setCleared(next)
    setDraft(
      components.map((c) => ({
        ...c,
        files: [
          ...(c.files ?? []).filter((f) => f.path !== path),
          ...(c.key === key ? [{ path, revision }] : []),
        ],
      })),
    )
  }
  const assignSheet = (sheet: string, key: string) => {
    const next = new Set(cleared)
    if (key === UNASSIGNED) next.add(`sheet:${sheet}`)
    else next.delete(`sheet:${sheet}`)
    setCleared(next)
    setDraft(
      components.map((c) => ({
        ...c,
        sheets: [
          ...(c.sheets ?? []).filter((s) => s !== sheet),
          ...(c.key === key ? [sheet] : []),
        ],
      })),
    )
  }
  const reset = () => {
    setDraft(null)
    setCleared(null)
    setSearch("")
  }
  const close = (saved = false) => {
    setOpen(false)
    reset()
    onClosed?.(saved)
  }
  const save = useMutation({
    mutationFn: () =>
      PartsService.saveComponentOrganization({
        partId,
        requestBody: {
          components: organization(),
          unassigned: unassigned(),
        },
      }),
    onSuccess: () => {
      for (const key of [
        "part-components",
        "part-evidence",
        "part-detail",
        "parts",
      ])
        void client.invalidateQueries({ queryKey: [key] })
      close(true)
    },
  })
  const term = search.trim().toLocaleLowerCase()
  const sources = allSources.filter((source) =>
    source.path.toLocaleLowerCase().includes(term),
  )
  const sheets = allSheets.filter((sheet) =>
    sheet.toLocaleLowerCase().includes(term),
  )
  const workbooks = query.data?.workbooks ?? []
  const choice = (
    label: string,
    owner: Owner,
    onChange: (key: string) => void,
  ) => (
    <Select
      disabled={save.isPending}
      value={owner.key ?? UNASSIGNED}
      onValueChange={onChange}
    >
      <SelectTrigger className="min-w-0 flex-1" aria-label={label}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={UNASSIGNED}>Sin asignar</SelectItem>
        {components.map((c) => (
          <SelectItem key={c.key} value={c.key}>
            {c.name || c.key}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
  const row = (
    key: string,
    icon: ReactNode,
    detail: string,
    name: string,
    title: string,
    owner: Owner,
    control: ReactNode,
  ) => (
    <div
      key={key}
      className="grid min-w-0 gap-2 rounded-md border px-2 py-2 sm:flex sm:items-center"
    >
      <div className="flex min-w-0 flex-1 items-center gap-2" title={title}>
        {icon}
        <div className="min-w-0">
          <p className="truncate text-xs text-muted-foreground">
            {detail}
            {owner.proposed && (
              <span className="ml-1 font-medium text-primary">· Propuesta</span>
            )}
          </p>
          <p className="truncate text-sm">{name}</p>
        </div>
      </div>
      <div className="flex min-w-0 gap-2 sm:w-56 sm:shrink-0">{control}</div>
    </div>
  )
  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className="h-8 shrink-0"
        onClick={() => setOpen(true)}
      >
        <Layers className="size-4" />
        Componentes
      </Button>
      <Dialog
        open={open}
        onOpenChange={(value) => {
          if (!save.isPending) {
            if (value) setOpen(true)
            else close()
          }
        }}
      >
        <DialogContent className="max-h-[85vh] grid-rows-[auto_minmax(0,1fr)_auto] sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>Componentes</DialogTitle>
            <DialogDescription>
              Sin componentes, la pieza se lee como una sola. Con ellos, cada
              archivo y hoja se asigna a uno; lo que coincide con su nombre
              aparece propuesto.
            </DialogDescription>
          </DialogHeader>
          <div className="min-h-0 overflow-y-auto">
            {query.isPending && (
              <div className="space-y-3 py-1">
                <output aria-label="Cargando componentes" className="sr-only">
                  Cargando
                </output>
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-36" />
              </div>
            )}
            {query.data && (
              <fieldset disabled={save.isPending} className="min-w-0 space-y-4">
                {!components.length && (
                  <p className="text-sm text-muted-foreground">
                    Sin componentes.
                  </p>
                )}
                <div className="flex flex-wrap gap-2">
                  {components.map((component, index) => (
                    <div
                      key={component.key}
                      className="flex w-full items-center gap-1 sm:w-56"
                    >
                      <Input
                        aria-label="Nombre"
                        autoFocus={!component.name}
                        placeholder="BASE, TAPA…"
                        value={component.name}
                        onChange={(e) =>
                          update(index, { name: e.target.value })
                        }
                        onBlur={(e) => {
                          const key = componentKey(e.target.value)
                          update(index, {
                            name: e.target.value,
                            ...(!query.data?.components?.some(
                              (c) => c.key === component.key,
                            ) &&
                            /^[A-Z]/.test(key) &&
                            !components.some(
                              (c, i) => i !== index && c.key === key,
                            )
                              ? { key }
                              : {}),
                          })
                        }}
                      />
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-9 shrink-0 text-muted-foreground"
                        aria-label={`Quitar componente ${component.name}`}
                        title="Quitar componente"
                        onClick={() =>
                          setDraft(components.filter((_, i) => i !== index))
                        }
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      let index = components.length + 1
                      while (components.some((c) => c.key === `COMP_${index}`))
                        index++
                      setDraft([
                        ...components,
                        {
                          key: `COMP_${index}`,
                          name: "",
                          sheets: [],
                          files: [],
                        },
                      ])
                    }}
                  >
                    <Plus className="size-4" />
                    Añadir componente
                  </Button>
                  {!components.length &&
                    (query.data.suggestions?.length ?? 0) > 0 && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setDraft(query.data!.suggestions!)}
                      >
                        Usar propuesta
                      </Button>
                    )}
                </div>
                {!!components.length &&
                  (query.data.unassigned_characteristics ?? 0) > 0 && (
                    <p className="text-sm text-muted-foreground">
                      {query.data.unassigned_characteristics} cotas anteriores
                      sin componente.
                    </p>
                  )}
                {!!components.length && (
                  <>
                    <SearchField
                      value={search}
                      onValueChange={setSearch}
                      onClear={() => setSearch("")}
                      aria-label="Buscar archivo"
                      placeholder="Buscar archivo u hoja…"
                    />
                    <section
                      aria-label="Hojas por componente"
                      className="space-y-2 border-t pt-4"
                    >
                      <h3 className="text-sm font-medium">Hojas de Excel</h3>
                      {sheets.map((sheet) => {
                        const books = workbooks.filter((w) =>
                          w.sheets?.includes(sheet),
                        ).length
                        return row(
                          `sheet:${sheet}`,
                          <FileSpreadsheet className="size-5 shrink-0 text-muted-foreground" />,
                          books
                            ? `Hoja · en ${books} ${books === 1 ? "libro" : "libros"}`
                            : "Hoja",
                          sheet,
                          sheet,
                          sheetOwner(sheet),
                          choice(
                            `Componente de la hoja ${sheet}`,
                            sheetOwner(sheet),
                            (key) => assignSheet(sheet, key),
                          ),
                        )
                      })}
                      {!sheets.length && (
                        <p className="text-sm text-muted-foreground">
                          Sin hojas.
                        </p>
                      )}
                    </section>
                    <section
                      aria-label="Archivos por componente"
                      className="space-y-2 border-t pt-4"
                    >
                      <h3 className="text-sm font-medium">Archivos</h3>
                      {sources.map((source) => {
                        const owner = fileOwner(source.path)
                        const file = components
                          .find((c) => c.key === owner.key)
                          ?.files?.find((f) => f.path === source.path)
                        const kind = source.kind as keyof typeof FILE_LABELS
                        const Icon = FILE_ICONS[kind] ?? FileSpreadsheet
                        return row(
                          source.path,
                          <Icon className="size-5 shrink-0 text-muted-foreground" />,
                          `${FILE_LABELS[kind] ?? "Informe"}${
                            source.path.includes("/")
                              ? ` · ${source.path.slice(0, source.path.lastIndexOf("/"))}`
                              : ""
                          }`,
                          source.path.split("/").pop()!,
                          source.path,
                          owner,
                          <>
                            {choice(
                              `Componente de ${source.path}`,
                              owner,
                              (key) =>
                                assignFile(source.path, key, file?.revision),
                            )}
                            {source.kind === "drawing" && owner.key && (
                              <Input
                                className="w-20 shrink-0"
                                aria-label={`Revisión de ${source.path}`}
                                placeholder="Rev."
                                value={file?.revision ?? ""}
                                onChange={(e) =>
                                  assignFile(
                                    source.path,
                                    owner.key!,
                                    e.target.value,
                                  )
                                }
                              />
                            )}
                          </>,
                        )
                      })}
                      {!sources.length && (
                        <p className="text-sm text-muted-foreground">
                          Sin archivos.
                        </p>
                      )}
                    </section>
                  </>
                )}
              </fieldset>
            )}
            {(query.error || save.error) && (
              <p role="alert" className="mt-3 text-sm text-destructive">
                {fileErrorMessage(query.error || save.error)}
              </p>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              disabled={save.isPending}
              onClick={() => close()}
            >
              Cancelar
            </Button>
            <Button
              disabled={
                !query.data ||
                (!draft && !proposals && !clearedDraft) ||
                save.isPending ||
                components.some((c) => !c.name.trim())
              }
              onClick={() => save.mutate()}
            >
              {save.isPending && <Loader2 className="size-4 animate-spin" />}
              Guardar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
