import { FilterSelect } from "@/components/Common/FilterSelect"
import { SearchToolbar } from "@/components/Common/SearchToolbar"
import { Button } from "@/components/ui/button"
import { CorrectionDetails } from "./Corrections"
import { CotaSearch } from "./CotaSearch"
import { correctionTimeline } from "./correctionTimeline"
import { DrawingToggle } from "./DrawingToggle"
import { MeasurementPlot, type PlotLine } from "./MeasurementPlot"
import {
  type PartSearch,
  selectEvaluation,
  visibleCavities,
} from "./measurementSelection"
import type { Study } from "./types"

export function Measurements({
  study,
  search,
  onChange,
  onDrawing,
}: {
  study: Study
  search: PartSearch
  onChange: (values: Partial<PartSearch>, replace?: boolean) => void
  onDrawing?: (code: string) => void
}) {
  const entries = study.catalog.entries
  const entry = search.cota
    ? entries.find(
        (item) =>
          item.id === search.cota || item.numbers.includes(search.cota!),
      )
    : (entries.find((item) => item.id === "N170") ?? entries[0])
  const code = search.cota ?? entry?.id ?? ""
  const selection = entry ? selectEvaluation(entry, search) : undefined
  const selected = selection?.selected
  const correctionMode = search.view === "correcciones"
  const visible = visibleCavities(study.cavities, search.cavities)
  const intervals =
    entry && selected ? correctionTimeline(study, entry, selected) : []
  const interval =
    intervals.find((item) => item.id === search.interval) ??
    intervals.find((item) => item.comparison) ??
    intervals.find((item) => item.actions.length) ??
    intervals[0]
  const cavity = visible.includes(search.cavity ?? "")
    ? search.cavity!
    : visible[0]
  const labels = study.samples.map((sample) => `intern.${sample}`)
  const lines: PlotLine[] = study.cavities.map((cavity) => ({
    name: cavity,
    points: study.samples.map(
      (sample) => selected?.series.records[cavity]?.[sample],
    ),
  }))
  const drawingCode = entry?.numbers.includes(code)
    ? code
    : (entry?.numbers[0] ?? code)
  return (
    <div className="space-y-5">
      <SearchToolbar
        action={
          <DrawingToggle
            disabled={!onDrawing || entry?.kind === "diagnostic"}
            onClick={() => onDrawing?.(drawingCode)}
          />
        }
      >
        <CotaSearch
          entries={entries}
          query={search.q ?? code}
          onQuery={(q) => onChange({ q }, true)}
          onSelect={(cota) =>
            onChange({
              cota,
              q: cota,
              element: undefined,
              height: undefined,
              evaluation: undefined,
              interval: undefined,
              action: undefined,
              view: undefined,
            })
          }
        />
      </SearchToolbar>
      <div className="flex justify-start">
        <Button
          size="sm"
          variant={correctionMode ? "secondary" : "outline"}
          aria-pressed={correctionMode}
          disabled={!interval && !correctionMode}
          onClick={() =>
            onChange({
              cota: code,
              interval: interval?.id,
              view: correctionMode ? undefined : "correcciones",
            })
          }
        >
          Correcciones
        </Button>
      </div>
      {!entry || !selected ? (
        <div className="rounded-lg border p-8 text-center text-sm text-muted-foreground">
          {code
            ? "Esta cota no tiene mediciones incorporadas. Puedes consultarla en el plano."
            : "Todavía no hay cotas con mediciones."}
        </div>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            {selection!.elements.length > 1 && (
              <FilterSelect
                label="Elemento"
                value={selected.element}
                options={selection!.elements.map((value) => ({
                  value,
                  label: value,
                }))}
                onChange={(element) =>
                  onChange(
                    {
                      cota: code,
                      element,
                      interval: correctionMode ? interval?.id : search.interval,
                    },
                    true,
                  )
                }
              />
            )}
            {selected.height && selection!.heights.length > 1 && (
              <FilterSelect
                label="Altura"
                value={selected.height}
                options={selection!.heights.map((value) => ({
                  value,
                  label: `${value.replace(".", ",")} mm`,
                }))}
                onChange={(height) =>
                  onChange(
                    {
                      cota: code,
                      element: selected.element,
                      height,
                      interval: correctionMode ? interval?.id : search.interval,
                    },
                    true,
                  )
                }
              />
            )}
            {selection!.evaluations.length > 1 && (
              <FilterSelect
                label="Evaluación"
                value={selected.metric}
                options={selection!.evaluations.map((item) => ({
                  value: item.metric,
                  label: item.label,
                }))}
                onChange={(evaluation) =>
                  onChange(
                    {
                      cota: code,
                      element: selected.element,
                      height: selected.height || undefined,
                      evaluation,
                      interval: correctionMode ? interval?.id : search.interval,
                    },
                    true,
                  )
                }
              />
            )}
          </div>
          <section
            className="space-y-3 rounded-lg border p-4 sm:p-5"
            aria-label={
              correctionMode
                ? "Evolución con correcciones"
                : "Evolución de mediciones"
            }
          >
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <h3 className="font-medium">Evolución de mediciones</h3>
              <span className="text-muted-foreground">{selected.label}</span>
            </div>
            <MeasurementPlot
              key={`${code}-${selected.series.id}`}
              labels={labels}
              lines={lines}
              unit={selected.series.unit}
              visible={visible}
              intervals={correctionMode ? intervals : undefined}
              selectedInterval={correctionMode ? interval?.id : undefined}
              onInterval={(id) =>
                onChange({ interval: id, action: undefined }, true)
              }
              onVisible={(names) =>
                onChange({ cota: code, cavities: names.join(",") }, true)
              }
            />
          </section>
          {correctionMode && interval && (
            <CorrectionDetails
              interval={interval}
              cota={code}
              evaluation={selected}
              cavities={visible}
              cavity={cavity}
              onCavity={(cavity) => onChange({ cavity }, true)}
              actionId={search.action}
              onAction={(action) => onChange({ action }, true)}
            />
          )}
        </>
      )}
    </div>
  )
}
