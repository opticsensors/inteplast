import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link, useBlocker, useNavigate } from "@tanstack/react-router"
import {
  ChevronRight,
  Files,
  FolderOpen,
  Layers,
  Loader2,
  Pencil,
  Ruler,
  Trash2,
  X,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import {
  ApiError,
  CatalogService,
  type FeaturePublic,
  FeaturesService,
  type PartDetailPublic,
  type PartPublic,
  PartsService,
} from "@/client"
import { CollapsibleSection } from "@/components/Common/CollapsibleSection"
import { FeatureThumbnail } from "@/components/Features/FeatureCard"
import {
  FEATURE_COLUMNS,
  FeatureBreadcrumb,
  FeatureSection,
} from "@/components/Features/FeatureLayout"
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
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { pickNativePath } from "@/lib/nativePicker"
import { AddFeatureButton } from "./AddFeatureButton"
import { FeaturePartEvidence } from "./FeaturePartEvidence"
import { MetrologyPage } from "./MetrologyPage"
import type { PartSearch } from "./measurementSelection"
import { PartCover } from "./PartCover"
import { PartFiles } from "./PartFiles"
import {
  PartReadButton,
  PartReadStatus,
  PIECE_QUERY_KEYS,
  usePartReading,
  useReadPartData,
} from "./PartReadStatus"
import { discoveredFiles, fileRequest, savedFiles } from "./pieceFileDrafts"

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
  return (
    <PartPage
      key={`${partId}:${Boolean(search.editar)}`}
      data={detail.data}
      search={search}
    />
  )
}

export function NewPartPage() {
  return <PartPage search={{}} />
}

function PartPage({
  data,
  search,
}: {
  data?: PartDetailPublic
  search: PartSearch
}) {
  const part = data?.part
  const editing = !part || Boolean(search.editar)
  const client = useQueryClient()
  const navigate = useNavigate()
  const initial = useRef({
    name: part?.name ?? "",
    description: part?.description ?? "",
    code: part?.code ?? "",
    customer: part?.customer ?? "",
    folder: part?.folder_path ?? "",
    files: savedFiles(data),
  }).current
  const [name, setName] = useState(initial.name)
  const [description, setDescription] = useState(initial.description)
  const [code, setCode] = useState(initial.code)
  const [customer, setCustomer] = useState(initial.customer)
  const [folder, setFolder] = useState(initial.folder)
  const [files, setFiles] = useState(initial.files)
  const [selectedFeatures, setSelectedFeatures] = useState<
    { id: string; name: string }[]
  >([])
  const [folderBusy, setFolderBusy] = useState(false)
  const [pickingFile, setPickingFile] = useState(false)
  const [folderError, setFolderError] = useState("")
  const [notices, setNotices] = useState<string[]>([])
  const [duplicate, setDuplicate] = useState<PartPublic>()
  const picker = useRef<AbortController | null>(null)
  const suggestedIdentity = useRef({ name: "", code: "" })
  const bypass = useRef(false)
  const dirty =
    editing &&
    (name !== initial.name ||
      description !== initial.description ||
      code !== initial.code ||
      customer !== initial.customer ||
      folder !== initial.folder ||
      JSON.stringify(fileRequest(files)) !==
        JSON.stringify(fileRequest(initial.files)) ||
      selectedFeatures.length > 0)
  const blocker = useBlocker({
    shouldBlockFn: ({ current, next }) =>
      !bypass.current && dirty && current.pathname !== next.pathname,
    enableBeforeUnload: () => dirty && !bypass.current,
    withResolver: true,
  })
  useEffect(() => () => picker.current?.abort(), [])
  const read = useReadPartData()
  const reading = usePartReading(part?.id)
  const invalidate = () =>
    Promise.all(
      PIECE_QUERY_KEYS.map((key) =>
        client.invalidateQueries({ queryKey: [key] }),
      ),
    )
  const setEditing = (value: boolean) => {
    if (part)
      void navigate({
        to: "/parts/$partId",
        params: { partId: part.id },
        search: { ...search, editar: value ? true : undefined },
        replace: true,
        resetScroll: false,
      })
  }
  const save = useMutation({
    mutationFn: () => {
      const values = {
        name: name.trim(),
        description: description.trim() || null,
        code: code.trim(),
        customer: customer.trim(),
        folder_path: folder || null,
        files: fileRequest(files),
      }
      return part
        ? PartsService.updatePart({ partId: part.id, requestBody: values })
        : PartsService.registerPart({
            requestBody: {
              ...values,
              folder_path: folder,
              feature_ids: selectedFeatures.map((feature) => feature.id),
            },
          })
    },
    onSuccess: async (saved) => {
      bypass.current = true
      await invalidate()
      if (!part || folder !== initial.folder) read.mutate(saved.id)
      if (part) setEditing(false)
      else
        void navigate({
          to: "/parts/$partId",
          params: { partId: saved.id },
          replace: true,
        })
    },
    onError: (error) => {
      const detail =
        error instanceof ApiError
          ? (error.body as { detail?: { part_id?: string } } | undefined)
              ?.detail
          : undefined
      if (typeof detail?.part_id === "string") {
        setDuplicate({
          id: detail.part_id,
          code: "",
          name: "esta carpeta",
        })
      }
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
      if (!part) return
      if (remove)
        await FeaturesService.unlinkFeaturePart({ featureId, partId: part.id })
      else await FeaturesService.linkFeaturePart({ featureId, partId: part.id })
    },
    onSuccess: invalidate,
  })
  const chooseFolder = async () => {
    const controller = new AbortController()
    picker.current = controller
    setFolderBusy(true)
    setFolderError("")
    try {
      const path = await pickNativePath("folder", controller.signal)
      if (!path || controller.signal.aborted) return
      const proposal = await PartsService.discoverPartFolder({
        requestBody: { folder_path: path },
      })
      if (controller.signal.aborted) return
      if (proposal.existing_part && proposal.existing_part.id !== part?.id) {
        setDuplicate(proposal.existing_part)
        return
      }
      setDuplicate(undefined)
      if (path === folder) return
      setFolder(path)
      setFiles(discoveredFiles(proposal))
      setNotices(proposal.notices ?? [])
      if (!part) {
        if (!name.trim() || name === suggestedIdentity.current.name)
          setName(proposal.name)
        if (!code.trim() || code === suggestedIdentity.current.code)
          setCode(proposal.code ?? "")
        suggestedIdentity.current = {
          name: proposal.name,
          code: proposal.code ?? "",
        }
      }
    } catch (error) {
      if (!controller.signal.aborted) setFolderError(fileErrorMessage(error))
    } finally {
      if (!controller.signal.aborted) setFolderBusy(false)
      picker.current = null
    }
  }
  const busy =
    save.isPending || membership.isPending || folderBusy || pickingFile
  const features: FeaturePublic[] = part ? data!.features : selectedFeatures
  const shownFiles = editing ? files : savedFiles(data)
  const cancel = () => {
    picker.current?.abort()
    bypass.current = true
    if (part) setEditing(false)
    else void navigate({ to: "/features", search: { kind: "part" } })
  }
  return (
    <div className="flex min-w-0 flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <FeatureBreadcrumb
          kind="part"
          name={part ? (part.name ?? part.code) : "Nueva pieza"}
        />
        <div className="flex flex-wrap items-center gap-2">
          {editing ? (
            <>
              <Button
                variant="outline"
                disabled={save.isPending || membership.isPending}
                onClick={cancel}
              >
                Cancelar
              </Button>
              <Button
                disabled={
                  busy ||
                  Boolean(duplicate) ||
                  (!folder && (!part || Boolean(initial.folder))) ||
                  (!part && !customer.trim()) ||
                  !name.trim() ||
                  !code.trim() ||
                  files.some((file) => !file.name.trim())
                }
                onClick={() => save.mutate()}
              >
                {save.isPending
                  ? "Guardando…"
                  : part
                    ? "Guardar cambios"
                    : "Crear pieza"}
              </Button>
            </>
          ) : (
            <Button
              variant="outline"
              className="border-primary text-primary hover:text-primary"
              onClick={() => setEditing(true)}
            >
              <Pencil />
              Editar pieza
            </Button>
          )}
        </div>
      </div>
      {save.error && !duplicate && (
        <p role="alert" className="text-sm text-destructive">
          {fileErrorMessage(save.error)}
        </p>
      )}
      <fieldset
        disabled={busy}
        className="flex min-w-0 flex-col gap-4 rounded-lg border bg-card p-4 sm:flex-row sm:gap-6 sm:p-5"
      >
        {part ? (
          <PartCover part={part} />
        ) : (
          <FeatureThumbnail
            feature={{ name: name || "Nueva pieza" }}
            className="size-32 sm:size-48"
          />
        )}
        <div className="min-w-0 flex-1 space-y-3">
          {editing ? (
            <>
              <div className="grid gap-2">
                <Label htmlFor="piece-name">Título</Label>
                <Input
                  id="piece-name"
                  aria-label="Nombre de la pieza"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  maxLength={255}
                  placeholder="Nombre de la pieza"
                  className="text-lg md:text-lg"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="piece-description">
                  Descripción{" "}
                  <span className="font-normal text-muted-foreground">
                    (opcional)
                  </span>
                </Label>
                <Textarea
                  id="piece-description"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  maxLength={2000}
                  placeholder="Descripción de la pieza"
                  className="min-h-16"
                />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="grid gap-2">
                  <Label htmlFor="piece-code">Código</Label>
                  <Input
                    id="piece-code"
                    aria-label="Código de la pieza"
                    value={code}
                    onChange={(event) => setCode(event.target.value)}
                    maxLength={64}
                    placeholder="Código de la pieza"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="piece-customer">Cliente</Label>
                  <Input
                    id="piece-customer"
                    value={customer}
                    onChange={(event) => setCustomer(event.target.value)}
                    maxLength={255}
                    placeholder="Nombre de la empresa"
                  />
                </div>
              </div>
            </>
          ) : (
            <>
              <h1 className="break-words text-2xl font-bold tracking-tight sm:text-3xl">
                {part?.name ?? part?.code}
              </h1>
              {part?.description && (
                <p className="whitespace-pre-wrap break-words text-muted-foreground">
                  {part.description}
                </p>
              )}
              <dl className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm">
                <div className="flex min-w-0 items-baseline gap-1.5">
                  <dt className="shrink-0 text-muted-foreground">Código:</dt>
                  <dd className="min-w-0 break-words">
                    {part?.code}
                    {part?.customer?.trim() && (
                      <span
                        aria-hidden="true"
                        className="ml-3 text-muted-foreground"
                      >
                        ·
                      </span>
                    )}
                  </dd>
                </div>
                {part?.customer?.trim() && (
                  <div className="flex min-w-0 items-baseline gap-1.5">
                    <dt className="shrink-0 text-muted-foreground">Cliente:</dt>
                    <dd className="min-w-0 break-words">
                      {part.customer.trim()}
                    </dd>
                  </div>
                )}
              </dl>
            </>
          )}
        </div>
      </fieldset>
      <section
        aria-label="Carpeta de la pieza"
        className="min-w-0 rounded-lg border bg-card px-4 py-2.5 sm:px-5"
      >
        <div className="flex min-w-0 items-center gap-3">
          <FolderOpen className="size-5 shrink-0 text-muted-foreground" />
          <h2 className="shrink-0 text-sm font-medium">Carpeta de la pieza</h2>
          <p
            className="min-w-0 flex-1 truncate text-sm text-muted-foreground"
            title={folder}
          >
            {folder ? folder.split("/").pop() : "Sin carpeta seleccionada"}
          </p>
          {editing && (
            <>
              <Button
                type="button"
                variant="outline"
                size={folder ? "icon" : "sm"}
                className={
                  folder ? "size-8 shrink-0" : "h-8 shrink-0 px-2 sm:px-3"
                }
                disabled={busy}
                aria-label={
                  folder ? "Cambiar carpeta de la pieza" : "Seleccionar carpeta"
                }
                onClick={() => void chooseFolder()}
              >
                {folderBusy ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <FolderOpen className="size-4" />
                )}
                {!folder && (
                  <span className="hidden sm:inline">Seleccionar carpeta</span>
                )}
              </Button>
              {folder && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-8 shrink-0"
                  aria-label="Quitar carpeta seleccionada"
                  disabled={busy}
                  onClick={() => {
                    setFolder("")
                    setFiles([])
                    setNotices([])
                    setDuplicate(undefined)
                  }}
                >
                  <X className="size-4" />
                </Button>
              )}
            </>
          )}
        </div>
        {editing && part && folder !== initial.folder && (
          <p className="mt-3 text-sm text-muted-foreground">
            Al guardar se vinculará esta carpeta y se leerán sus datos.
          </p>
        )}
        {notices.map((notice) => (
          <p key={notice} className="mt-2 text-sm text-muted-foreground">
            {notice}
          </p>
        ))}
        {folderError && (
          <p role="alert" className="mt-2 text-sm text-destructive">
            {folderError}
          </p>
        )}
        {duplicate && (
          <p role="alert" className="mt-2 text-sm">
            Esta carpeta ya pertenece a {duplicate.name ?? duplicate.code}.{" "}
            <Link
              to="/parts/$partId"
              params={{ partId: duplicate.id }}
              className="font-medium text-primary underline"
            >
              Abrir la pieza existente
            </Link>
          </p>
        )}
      </section>
      <div className={FEATURE_COLUMNS}>
        <section
          id="cotas"
          className="min-w-0 scroll-mt-6"
          aria-label="Cotas de la pieza"
        >
          <FeatureSection
            title="Cotas"
            count={part?.characteristic_count ?? 0}
            icon={<Ruler className="size-5 shrink-0 text-muted-foreground" />}
            actions={
              <PartReadButton
                reading={reading}
                folder={part?.folder_path}
                editing={editing}
              />
            }
          >
            {part ? (
              <>
                <PartReadStatus reading={reading} />
                <MetrologyPage partId={part.id} search={search} embedded />
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                {folder
                  ? "Las cotas se extraerán automáticamente al crear la pieza. Aquí podrás consultar sus mediciones y correcciones."
                  : "Selecciona la carpeta de la pieza. Las cotas se leerán de sus ficheros al crearla."}
              </p>
            )}
          </FeatureSection>
        </section>
        <div className="min-w-0 space-y-5">
          <FeatureSection
            title="Features"
            count={features.length}
            icon={<Layers className="size-5 shrink-0 text-muted-foreground" />}
          >
            <div className="space-y-3">
              {features.map((feature) => (
                <section
                  key={feature.id}
                  aria-label={`Feature ${feature.name}`}
                >
                  <CollapsibleSection
                    compact
                    title={feature.name}
                    className="bg-muted/20"
                    storageKey={`piece-feature:${part?.id ?? "new"}:${feature.id}`}
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
                            disabled={busy}
                            onClick={() =>
                              part
                                ? membership.mutate({
                                    featureId: feature.id,
                                    remove: true,
                                  })
                                : setSelectedFeatures((current) =>
                                    current.filter(
                                      (item) => item.id !== feature.id,
                                    ),
                                  )
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
                    {part && "assets" in feature ? (
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
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        Se vinculará al crear la pieza.
                      </p>
                    )}
                  </CollapsibleSection>
                </section>
              ))}
              {!features.length && (
                <p className="text-sm text-muted-foreground">
                  Sin features vinculados.
                </p>
              )}
              {editing && (
                <AddFeatureButton
                  linkedIds={features.map((feature) => feature.id)}
                  disabled={busy}
                  onSelect={(id, featureName) =>
                    part
                      ? membership.mutate({ featureId: id })
                      : setSelectedFeatures((current) => [
                          ...current,
                          { id, name: featureName },
                        ])
                  }
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
            count={shownFiles.length}
            icon={<Files className="size-5 shrink-0 text-muted-foreground" />}
          >
            <PartFiles
              files={shownFiles}
              folder={folder}
              partId={part?.id}
              editing={editing}
              disabled={save.isPending || folderBusy}
              onChange={setFiles}
              onPickingChange={setPickingFile}
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
              Si sales ahora se descartarán los cambios de esta ficha.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => blocker.reset?.()}>
              Seguir editando
            </Button>
            <Button variant="destructive" onClick={() => blocker.proceed?.()}>
              Descartar y salir
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
