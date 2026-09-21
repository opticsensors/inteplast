import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { type ReactNode, useEffect, useMemo, useState } from "react"
import { EvidenceService, type FilePublic } from "@/client"
import { SearchField } from "@/components/Common/SearchField"
import { SearchToolbar } from "@/components/Common/SearchToolbar"
import { Button } from "@/components/ui/button"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { matchesCotaPrefix, normalizeCota } from "./drawingSearchHelpers"
import PdfViewer from "./PdfViewer"

export type DrawingFocus = { id: string; page: number; box: number[] }
type Candidate = DrawingFocus & {
  candidates?: { label: string }[]
  text?: string
  method?: string
}
type Index = {
  balloons: Candidate[]
  words: Candidate[]
  notices: string[]
}

export default function DrawingSearch({
  file,
  title,
  initialQuery = "",
  searchAction,
  onQueryChange,
  allowedCotas,
  context,
  searchFilters,
}: {
  file: FilePublic
  title: string
  initialQuery?: string
  searchAction?: ReactNode
  onQueryChange?: (query: string) => void
  allowedCotas?: string[]
  context?: string
  searchFilters?: ReactNode
}) {
  const client = useQueryClient()
  const [query, setQuery] = useState(initialQuery)
  const [selectedId, setSelectedId] = useState("")
  const key = ["drawing-index", file.id, file.version]
  const index = useQuery({
    queryKey: key,
    queryFn: () => EvidenceService.readDrawingIndex({ fileId: file.id }),
    refetchInterval: (q) =>
      ["queued", "processing"].includes(q.state.data?.state ?? "")
        ? 2000
        : false,
    retry: false,
  })
  const prepare = useMutation({
    mutationFn: () => EvidenceService.indexDrawing({ fileId: file.id }),
    onSuccess: () => client.invalidateQueries({ queryKey: key }),
  })
  const data =
    index.data?.state === "ready" ? (index.data.payload as Index) : undefined
  const results = useMemo(() => {
    if (!data || !query.trim()) return []
    const reviews = new Map(
      (index.data?.reviews ?? []).map((r) => [r.candidate_id, r]),
    )
    const needle = normalizeCota(query)
    return [
      ...data.balloons,
      ...data.words.filter(
        (word) =>
          /^N?\d+(?:\.\d+)?$/.test((word.text ?? "").trim()) &&
          (word.method === "pdf" || /^N\d/.test(word.text ?? "")),
      ),
    ]
      .flatMap((candidate) => {
        const review = reviews.get(candidate.id)
        const labels = review
          ? [review.label]
          : (candidate.candidates?.map((item) => item.label) ?? [
              normalizeCota(candidate.text ?? ""),
            ])
        const matches = labels.filter(
          (label) =>
            matchesCotaPrefix(label, needle) &&
            (!allowedCotas ||
              allowedCotas.some(
                (code) => label === code || label.startsWith(`${code}.`),
              )),
        )
        return matches.length
          ? [
              {
                ...candidate,
                label: matches.join(" / "),
                exact: matches.includes(needle),
              },
            ]
          : []
      })
      .sort(
        (a, b) =>
          Number(b.exact) - Number(a.exact) ||
          a.page - b.page ||
          a.box[1] - b.box[1],
      )
  }, [data, index.data?.reviews, query, allowedCotas])
  const selected =
    results.find((result) => result.id === selectedId) ?? results[0]
  // biome-ignore lint/correctness/useExhaustiveDependencies: Each document starts with its own search.
  useEffect(() => {
    setQuery(initialQuery)
    setSelectedId("")
  }, [initialQuery, file.id])
  const working =
    prepare.isPending ||
    ["queued", "processing"].includes(index.data?.state ?? "")
  const changeQuery = (value: string) => {
    setQuery(value)
    setSelectedId("")
    onQueryChange?.(value)
  }
  return (
    <div className="flex flex-col gap-3">
      <SearchToolbar action={searchAction}>
        <SearchField
          aria-label="Buscar cota en el plano"
          placeholder="Buscar cota por número…"
          value={query}
          onValueChange={changeQuery}
          onClear={() => changeQuery("")}
        />
      </SearchToolbar>
      {searchFilters}
      {context && <p className="text-sm text-muted-foreground">{context}</p>}
      {!data && (
        <div>
          <Button
            variant="outline"
            size="sm"
            disabled={working || index.isPending}
            onClick={() => prepare.mutate()}
          >
            {working ? "Preparando búsqueda…" : "Preparar búsqueda"}
          </Button>
        </div>
      )}
      {(index.error || prepare.error) && (
        <p role="alert" className="text-sm text-destructive">
          {fileErrorMessage(index.error || prepare.error)}
        </p>
      )}
      {index.data?.message && (
        <p className="text-sm text-muted-foreground">{index.data.message}</p>
      )}
      {data && query.trim() && (
        <div className="flex flex-wrap items-start gap-3">
          <output className="py-2 text-xs text-muted-foreground">
            {results.length} {results.length === 1 ? "resultado" : "resultados"}
          </output>
          <fieldset className="flex max-h-28 min-w-0 flex-1 flex-wrap gap-2 overflow-y-auto p-1">
            <legend className="sr-only">Coincidencias en el plano</legend>
            {results.map((result) => {
              const repeated = results.filter(
                (item) => item.label === result.label,
              )
              const label =
                repeated.length > 1
                  ? `${result.label} · ${repeated.findIndex((item) => item.id === result.id) + 1}/${repeated.length}`
                  : result.label
              return (
                <Button
                  key={result.id}
                  type="button"
                  variant={result.id === selected?.id ? "secondary" : "outline"}
                  size="sm"
                  onClick={() => setSelectedId(result.id)}
                  aria-pressed={result.id === selected?.id}
                  title={`Página ${result.page}`}
                >
                  {label}
                </Button>
              )
            })}
          </fieldset>
        </div>
      )}
      <PdfViewer file={file} title={title} focus={selected} />
      {data?.notices?.length ? (
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer">
            Notas de lectura ({data.notices.length})
          </summary>
          {data.notices.map((notice) => (
            <p className="mt-1" key={notice}>
              {notice}
            </p>
          ))}
        </details>
      ) : null}
    </div>
  )
}
