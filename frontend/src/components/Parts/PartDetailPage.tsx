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
import { COVER_SIZE } from "@/components/Features/CoverButton"
import { FeatureThumbnail } from "@/components/Features/FeatureCard"
import {
  FEATURE_COLUMNS,
  FeatureBreadcrumb,
  FeatureSection,
} from "@/components/Features/FeatureLayout"
import {
  partClassification,
  partLabel,
  partName,
} from "@/components/Features/parts"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
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
import useAuth from "@/hooks/useAuth"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { pickSourcePath } from "@/lib/sourcePicker"
import { AddFeatureButton } from "./AddFeatureButton"
import { CatalogNameSelect } from "./CatalogNameSelect"
import { DeletePart } from "./DeletePart"
import { FeaturePartEvidence } from "./FeaturePartEvidence"
import { MetrologyPage } from "./MetrologyPage"
import type { PartSearch } from "./measurementSelection"
import { PartComponents } from "./PartComponents"
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
  const { user } = useAuth()
  const initial = useRef({
    name: part?.name ?? "",
    description: part?.description ?? "",
    code: part?.code ?? "",
    familyId: part?.family_id ?? null,
    customerId: part?.customer_id ?? null,
    materialId: part?.material_id ?? null,
    cavities: part?.cavity_count?.toString() ?? "",
    folder: part?.folder_path ?? "",
    files: savedFiles(data),
  }).current
  const [name, setName] = useState(initial.name)
  const [description, setDescription] = useState(initial.description)
  const [code, setCode] = useState(initial.code)
  const [familyId, setFamilyId] = useState(initial.familyId)
  const [customerId, setCustomerId] = useState(initial.customerId)
  const [materialId, setMaterialId] = useState(initial.materialId)
  const [cavities, setCavities] = useState(initial.cavities)
  const [invalidCavities, setInvalidCavities] = useState(false)
  const [folder, setFolder] = useState(initial.folder)
  const [organizeBeforeReading, setOrganizeBeforeReading] = useState(false)
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
  const suggestedFeatures = useRef<string[]>([])
  const bypass = useRef(false)
  const dirty =
    editing &&
    (name !== initial.name ||
      description !== initial.description ||
      code !== initial.code ||
      familyId !== initial.familyId ||
      customerId !== initial.customerId ||
      materialId !== initial.materialId ||
      cavities !== initial.cavities ||
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
        name: name.trim() || null,
        description: description.trim() || null,
        code: code.trim(),
        family_id: familyId,
        customer_id: customerId,
        material_id: materialId,
        cavity_count: cavities ? Number(cavities) : null,
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
      if ((!part || folder !== initial.folder) && !organizeBeforeReading)
        read.mutate(saved.id)
      if (part) setEditing(false)
      else
        void navigate({
          to: "/parts/$partId",
          params: { partId: saved.id },
          search: organizeBeforeReading ? { componentes: true } : {},
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
      const path = await pickSourcePath("folder", controller.signal)
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
        // Features named like a folder above the piece: proposed, removable, and
        // replaced only when another folder is chosen. Manual choices stay.
        // Only what the suggestion itself added is replaced later: a feature the user
        // had already chosen stays theirs even if a folder also suggests it.
        const proposed = proposal.suggested_features ?? []
        const previous = suggestedFeatures.current
        setSelectedFeatures((current) => {
          const kept = current.filter((item) => !previous.includes(item.id))
          const added = proposed.filter(
            (item) => !kept.some((chosen) => chosen.id === item.id),
          )
          // Same result if React calls this twice: it depends only on `current`.
          suggestedFeatures.current = added.map((item) => item.id)
          return [...kept, ...added.map(({ id, name }) => ({ id, name }))]
        })
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
    <div className="@container flex min-w-0 flex-col gap-5">
      <div className="grid items-center gap-3 @min-[34rem]:grid-cols-[minmax(0,1fr)_16rem]">
        <FeatureBreadcrumb
          kind="part"
          name={part ? partLabel(part) : "Nueva pieza"}
        />
        <div className="flex flex-wrap items-center gap-2 @min-[34rem]:justify-end">
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
                  !code.trim() ||
                  invalidCavities ||
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
            <>
              <Button
                variant="outline"
                className="border-primary text-primary hover:text-primary"
                onClick={() => setEditing(true)}
              >
                <Pencil />
                Editar pieza
              </Button>
              {part && user?.is_superuser && (
                <DeletePart
                  partId={part.id}
                  onDeleted={() => {
                    bypass.current = true
                    void navigate({
                      to: "/features",
                      search: { kind: "part" },
                      replace: true,
                    })
                  }}
                />
              )}
            </>
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
        className="flex min-w-0 flex-col gap-4 rounded-lg border bg-card p-4 sm:gap-6 sm:p-5 lg:flex-row"
      >
        {part ? (
          <PartCover part={part} />
        ) : (
          <FeatureThumbnail
            feature={{ name: name || "Nueva pieza" }}
            className={COVER_SIZE}
          />
        )}
        <div
          className={
            editing
              ? "flex min-w-0 flex-1 flex-col gap-3"
              : "min-w-0 flex-1 space-y-3"
          }
        >
          {editing ? (
            <>
              {/* El código es el título; el nombre, opcional, va a su lado. */}
              <div className="grid gap-3 sm:grid-cols-[minmax(0,11rem)_minmax(0,1fr)]">
                <div className="grid gap-2">
                  <Label htmlFor="piece-code">Código</Label>
                  <Input
                    id="piece-code"
                    aria-label="Código de la pieza"
                    value={code}
                    onChange={(event) => setCode(event.target.value)}
                    maxLength={64}
                    placeholder="3212"
                    className="h-11 font-semibold text-lg md:text-lg"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="piece-name">
                    Nombre{" "}
                    <span className="font-normal text-muted-foreground">
                      (opcional)
                    </span>
                  </Label>
                  <Input
                    id="piece-name"
                    aria-label="Nombre de la pieza"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    maxLength={255}
                    placeholder="Nombre de la pieza"
                    className="h-11 text-lg md:text-lg"
                  />
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[repeat(3,minmax(0,1fr))_7rem]">
                <CatalogNameSelect
                  kind="families"
                  value={familyId}
                  selected={part?.family}
                  onChange={setFamilyId}
                  disabled={busy}
                />
                <CatalogNameSelect
                  kind="customers"
                  value={customerId}
                  selected={part?.customer}
                  onChange={setCustomerId}
                  disabled={busy}
                />
                <CatalogNameSelect
                  kind="materials"
                  value={materialId}
                  selected={part?.material}
                  onChange={setMaterialId}
                  disabled={busy}
                />
                <fieldset className="min-w-0">
                  <legend className="mb-1.5 text-sm font-medium">
                    <label htmlFor="piece-cavities">Nº de cavidades</label>
                  </legend>
                  <Input
                    id="piece-cavities"
                    type="number"
                    min={1}
                    max={2147483647}
                    step={1}
                    inputMode="numeric"
                    value={cavities}
                    aria-invalid={invalidCavities}
                    onChange={(event) => {
                      setCavities(event.currentTarget.value)
                      setInvalidCavities(!event.currentTarget.validity.valid)
                    }}
                  />
                </fieldset>
              </div>
              <div className="flex flex-1 flex-col gap-2">
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
                  className="min-h-16 flex-1 lg:field-sizing-fixed lg:resize-none"
                />
              </div>
            </>
          ) : (
            <>
              <h1 className="break-words text-2xl font-bold tracking-tight sm:text-3xl">
                {part?.code}
                {part && partName(part) && (
                  <>
                    {" "}
                    <span className="ml-1 font-normal text-muted-foreground">
                      {partName(part)}
                    </span>
                  </>
                )}
              </h1>
              {part && partClassification(part) && (
                <p className="break-words text-sm text-muted-foreground">
                  {partClassification(part)}
                </p>
              )}
              {(part?.material || part?.cavity_count != null) && (
                <dl className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
                  {part.material && (
                    <div className="flex gap-2">
                      <dt className="text-muted-foreground">Material</dt>
                      <dd>{part.material.name}</dd>
                    </div>
                  )}
                  {part.cavity_count != null && (
                    <div className="flex gap-2">
                      <dt className="text-muted-foreground">Nº de cavidades</dt>
                      <dd>{part.cavity_count}</dd>
                    </div>
                  )}
                </dl>
              )}
              {part?.description && (
                <p className="whitespace-pre-wrap break-words text-muted-foreground">
                  {part.description}
                </p>
              )}
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
          {part && !editing && part.folder_path && (
            <PartComponents
              partId={part.id}
              defaultOpen={Boolean(search.componentes)}
              onClosed={() => {
                if (!search.componentes) return
                // With or without components: without them it reads as one piece.
                read.mutate(part.id)
                void navigate({
                  to: "/parts/$partId",
                  params: { partId: part.id },
                  search: { ...search, componentes: undefined },
                  replace: true,
                  resetScroll: false,
                })
              }}
            />
          )}
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
        {!part && folder && (
          <div className="mt-3 space-y-2">
            <Label className="flex items-center gap-2">
              <Checkbox
                disabled={busy}
                checked={organizeBeforeReading}
                onCheckedChange={(value) =>
                  setOrganizeBeforeReading(value === true)
                }
              />
              Varios componentes
            </Label>
          </div>
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
            Esta carpeta ya pertenece a{" "}
            {duplicate.code ? partLabel(duplicate) : duplicate.name}.{" "}
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
                {organizeBeforeReading
                  ? "Al crear la pieza podrás nombrar sus componentes y revisar qué archivos y hojas corresponden a cada uno. Después se leerán sus datos; sin componentes, como una pieza normal."
                  : folder
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
