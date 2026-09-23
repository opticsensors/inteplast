import { useQuery } from "@tanstack/react-query"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"
import { FilesService } from "@/client"
import { SearchField } from "@/components/Common/SearchField"
import { Button } from "@/components/ui/button"
import { fileErrorMessage } from "@/hooks/useFileAccess"
import { cn } from "@/lib/utils"
import { columnLabel, searchCells, sourcePosition } from "./sourceTableHelpers"

const PAGE_SIZE = 80

export default function SourceTableViewer({
  fileId,
  version,
  query,
  locator,
  cavity,
  value,
  onQuery,
}: {
  fileId: string
  version?: string | null
  query: string
  locator?: string
  cavity?: string
  value?: string
  onQuery: (query: string) => void
}) {
  const result = useQuery({
    queryKey: ["source-table", fileId, version],
    queryFn: () => FilesService.readSourceTable({ fileId }),
    retry: false,
    staleTime: 60_000,
  })
  const sheets = result.data?.sheets
  const origin = useMemo(
    () => sourcePosition(sheets ?? [], locator ?? "", cavity, value),
    [sheets, locator, cavity, value],
  )
  const matches = useMemo(
    () =>
      query === locator && origin ? [origin] : searchCells(sheets ?? [], query),
    [sheets, query, locator, origin],
  )
  const [selection, setSelection] = useState({ query, match: 0 })
  const match = selection.query === query ? selection.match : 0
  const setMatch = (match: number) => setSelection({ query, match })
  const [sheet, setSheet] = useState(0)
  const [page, setPage] = useState(0)
  const highlighted = useRef<HTMLTableCellElement>(null)
  const current = matches[Math.min(match, Math.max(0, matches.length - 1))]
  useEffect(() => {
    if (!current) return
    setSheet(current.sheet)
    setPage(Math.floor(current.row / PAGE_SIZE))
  }, [current])
  useEffect(() => {
    if (
      !current ||
      current.sheet !== sheet ||
      Math.floor(current.row / PAGE_SIZE) !== page
    )
      return
    highlighted.current?.scrollIntoView({ block: "nearest", inline: "center" })
  }, [current, sheet, page])
  const selected = sheets?.[sheet]
  const rows = selected?.rows ?? []
  const columns = rows.reduce((max, row) => Math.max(max, row.length), 0)
  const lastPage = Math.max(0, Math.ceil(rows.length / PAGE_SIZE) - 1)
  const isCurrent = (r: number, c: number) =>
    current?.sheet === sheet &&
    current.row === r &&
    (current.column === undefined || current.column === c)
  return (
    <section aria-label="Archivo de origen" className="min-w-0 space-y-3">
      <SearchField
        aria-label="Buscar en el archivo"
        placeholder="Buscar texto, valor o referencia de celda…"
        value={query}
        onValueChange={onQuery}
        onClear={() => onQuery("")}
        onKeyDown={(event) => {
          if (event.key === "Enter" && matches.length)
            setMatch(
              (match + (event.shiftKey ? matches.length - 1 : 1)) %
                matches.length,
            )
        }}
      />
      {result.isPending ? (
        <output>Cargando archivo original…</output>
      ) : result.error ? (
        <p role="alert">{fileErrorMessage(result.error)}</p>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
            <div className="flex items-center gap-2">
              <output>
                {query.trim()
                  ? matches.length
                    ? `${Math.min(match + 1, matches.length)} de ${matches.length}${matches.length === 1000 ? "+" : ""} resultados`
                    : "Sin resultados"
                  : "Contenido del archivo original"}
              </output>
              {matches.length > 1 && (
                <>
                  <Button
                    size="icon"
                    variant="outline"
                    aria-label="Resultado anterior"
                    onClick={() =>
                      setMatch((match + matches.length - 1) % matches.length)
                    }
                  >
                    <ChevronLeft />
                  </Button>
                  <Button
                    size="icon"
                    variant="outline"
                    aria-label="Resultado siguiente"
                    onClick={() => setMatch((match + 1) % matches.length)}
                  >
                    <ChevronRight />
                  </Button>
                </>
              )}
            </div>
            {locator && query !== locator && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onQuery(locator)}
              >
                Volver al origen de la medición
              </Button>
            )}
          </div>
          {locator && query === locator && !origin && (
            <p className="text-sm text-muted-foreground">
              No se ha localizado la referencia guardada. Puedes buscar en el
              contenido del archivo.
            </p>
          )}
          <div
            className="flex max-w-full gap-1 overflow-x-auto"
            role="tablist"
            aria-label="Hojas del archivo"
          >
            {sheets?.map((item, index) => (
              <Button
                key={item.name}
                id={`sheet-tab-${index}`}
                role="tab"
                aria-selected={sheet === index}
                aria-controls="source-sheet"
                variant={sheet === index ? "secondary" : "ghost"}
                size="sm"
                onClick={() => {
                  setSheet(index)
                  setPage(0)
                }}
              >
                {item.name}
              </Button>
            ))}
          </div>
          <div
            id="source-sheet"
            role="tabpanel"
            aria-labelledby={`sheet-tab-${sheet}`}
            className="max-h-[65vh] max-w-full overflow-auto rounded-lg border"
          >
            <table
              className="w-full border-collapse text-xs"
              aria-label={`Contenido de ${selected?.name ?? "archivo"}`}
            >
              <thead className="sticky top-0 z-10 bg-muted">
                <tr>
                  <th
                    className="sticky left-0 z-20 border-r bg-muted p-2"
                    scope="col"
                  >
                    Fila
                  </th>
                  {Array.from({ length: columns }, (_, c) => (
                    <th
                      key={c}
                      scope="col"
                      className="min-w-24 border-r px-3 py-2 font-medium"
                    >
                      {columnLabel(c)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows
                  .slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
                  .map((cells, index) => {
                    const r = page * PAGE_SIZE + index
                    return (
                      <tr key={r}>
                        <th
                          scope="row"
                          className="sticky left-0 border-t border-r bg-muted px-3 py-2 font-normal tabular-nums"
                        >
                          {r + 1}
                        </th>
                        {Array.from({ length: columns }, (_, c) => (
                          <td
                            key={c}
                            ref={
                              isCurrent(r, c) &&
                              (current?.column !== undefined || c === 0)
                                ? highlighted
                                : undefined
                            }
                            aria-current={isCurrent(r, c) ? "true" : undefined}
                            title={`${selected?.name}!${columnLabel(c)}${r + 1}`}
                            className={cn(
                              "max-w-96 whitespace-pre-wrap break-words border-t border-r px-3 py-2 align-top tabular-nums",
                              isCurrent(r, c) &&
                                "bg-amber-100 font-semibold text-amber-950 outline-2 -outline-offset-2 outline-amber-500",
                            )}
                          >
                            {cells[c] ?? ""}
                          </td>
                        ))}
                      </tr>
                    )
                  })}
              </tbody>
            </table>
            {!rows.length && (
              <p className="p-6 text-sm text-muted-foreground">Hoja vacía.</p>
            )}
          </div>
          <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
            <span>
              {rows.length
                ? `Filas ${page * PAGE_SIZE + 1}–${Math.min((page + 1) * PAGE_SIZE, rows.length)} de ${rows.length}`
                : "0 filas"}
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={!page}
                onClick={() => setPage(page - 1)}
              >
                Anterior
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={page >= lastPage}
                onClick={() => setPage(page + 1)}
              >
                Siguiente
              </Button>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            Vista de solo lectura. Los Excel muestran los valores guardados en
            el archivo.
          </p>
        </>
      )}
    </section>
  )
}
