import { X } from "lucide-react"
import { useEffect, useId, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { fmt } from "./EvidenceElements"
import type { Measurement } from "./types"

export type PlotPoint = Partial<Measurement> & {
  value: number | null
  prediction?: boolean
  connectorOnly?: boolean
  label?: string
  change?: number | null
}
export type PlotLine = {
  id?: string
  name: string
  points: (PlotPoint | null | undefined)[]
}
type Hit = {
  id: string
  point: PlotPoint
  name: string
  index: number
  value: number
  x: number
  y: number
  color: string
}
const colors = ["#2563eb", "#8b5cf6", "#d97706", "#0891b2"]
const finite = (value: number | null | undefined): value is number =>
  value != null && Number.isFinite(value)

/** Hit-test the visible points, never the empty area of a sample column. */
export function MeasurementPlot({
  labels,
  lines,
  visible,
  onVisible,
  unit = "mm",
  intervals,
  selectedInterval,
  onInterval,
  empty = false,
  onSource,
}: {
  labels: string[]
  lines: PlotLine[]
  visible: string[]
  onVisible?: (names: string[]) => void
  unit?: string
  intervals?: { id: string; from: number; to: number }[]
  selectedInterval?: string
  onInterval?: (id: string) => void
  empty?: boolean
  onSource?: (point: PlotPoint, cavity: string) => void
}) {
  const tooltipId = useId()
  const [active, setActive] = useState<Hit | null>(null)
  const [pinned, setPinned] = useState(false)
  const plot = useRef<HTMLDivElement>(null)
  const [plotWidth, setPlotWidth] = useState(740)
  useEffect(() => {
    const node = plot.current
    if (!node) return
    const observer = new ResizeObserver(() => {
      setPlotWidth(Math.max(1, node.clientWidth))
      setActive(null)
      setPinned(false)
    })
    observer.observe(node)
    const dismiss = (event: PointerEvent) => {
      if (!node.contains(event.target as Node)) {
        setActive(null)
        setPinned(false)
      }
    }
    const dismissOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setActive(null)
        setPinned(false)
      }
    }
    document.addEventListener("pointerdown", dismiss)
    document.addEventListener("keydown", dismissOnEscape)
    return () => {
      observer.disconnect()
      document.removeEventListener("pointerdown", dismiss)
      document.removeEventListener("keydown", dismissOnEscape)
    }
  }, [])
  const names = [...new Set(lines.map((line) => line.name))]
  const color = (name: string) => colors[names.indexOf(name) % colors.length]
  const shown = lines.filter((line) => visible.includes(line.name))
  const points = shown
    .flatMap((line) => line.points)
    .filter((point): point is PlotPoint => Boolean(point))
  const values = points.map((point) => point.value).filter(finite)
  const limits = points
    .flatMap((point) => [point.lower, point.upper])
    .filter(finite)
  const first = points.find(
    (point) => finite(point.lower) && finite(point.upper),
  )
  const sameLimits =
    first &&
    points.every(
      (point) => point.lower === first.lower && point.upper === first.upper,
    )
  const all = [...values, ...limits]
  const pad = all.length
    ? Math.max((Math.max(...all) - Math.min(...all)) * 0.15, 0.01)
    : 1
  const min = (all.length ? Math.min(...all) : 0) - pad
  const max = (all.length ? Math.max(...all) : 1) + pad
  const x = (index: number) =>
    labels.length === 1
      ? plotWidth / 2
      : 64 + (index * (plotWidth - 128)) / (labels.length - 1)
  const compactLabels =
    labels.length > 1 && (plotWidth - 128) / (labels.length - 1) < 64
  const y = (value: number) => 235 - ((value - min) / (max - min)) * 190
  const hits: Hit[] = lines.flatMap((line) =>
    visible.includes(line.name)
      ? line.points.flatMap((point, index) =>
          point && !point.connectorOnly && finite(point.value)
            ? [
                {
                  id: `${line.id ?? line.name}-${index}`,
                  point,
                  name: line.name,
                  index,
                  value: point.value,
                  x: x(index),
                  y: y(point.value),
                  color: color(line.name),
                },
              ]
            : [],
        )
      : [],
  )
  const hitAt = (clientX: number, clientY: number, radius = 8) => {
    const bounds = plot.current?.getBoundingClientRect()
    if (!bounds) return null
    const px = clientX - bounds.left
    const py = clientY - bounds.top
    let nearest: Hit | null = null
    let distance = radius
    for (const hit of hits) {
      const candidate = Math.hypot(hit.x - px, hit.y - py)
      if (candidate <= distance) {
        nearest = hit
        distance = candidate
      }
    }
    return nearest
  }
  // Nearly coincident cavities share a tooltip; a distant point in the same sample does not.
  const overlapping = active
    ? hits.filter(
        (hit) =>
          hit.index === active.index &&
          Math.hypot(hit.x - active.x, hit.y - active.y) <= 4,
      )
    : []
  const detailed = overlapping.some((hit) => hit.point.label)
  const tooltipWidth = Math.min(detailed ? 260 : 184, plotWidth - 16)
  const tooltipHeight = Math.min(
    240,
    44 + overlapping.length * (detailed ? 54 : 24),
  )
  const tooltipLeft = active
    ? Math.max(
        8,
        Math.min(
          active.x + 12 + tooltipWidth <= plotWidth - 8
            ? active.x + 12
            : active.x - tooltipWidth - 12,
          plotWidth - tooltipWidth - 8,
        ),
      )
    : 0
  const tooltipTop = active
    ? Math.max(
        8,
        active.y + 12 + tooltipHeight <= 285
          ? active.y + 12
          : active.y - tooltipHeight - 12,
      )
    : 0
  const toggle = (name: string) => {
    if (visible.includes(name) && visible.length === 1) return
    onVisible?.(
      visible.includes(name)
        ? visible.filter((item) => item !== name)
        : [...visible, name],
    )
    setActive(null)
    setPinned(false)
  }
  return (
    <div className="min-w-0 space-y-3">
      <div
        ref={plot}
        className="relative"
        onPointerMove={(event) => {
          if (!pinned && event.pointerType !== "touch")
            setActive(hitAt(event.clientX, event.clientY))
        }}
        onPointerDown={(event) => {
          if ((event.target as Element).closest("[data-plot-popover]")) return
          const hit = hitAt(
            event.clientX,
            event.clientY,
            event.pointerType === "touch" ? 16 : 8,
          )
          if (!hit) {
            setActive(null)
            setPinned(false)
          } else if (event.pointerType === "touch") {
            setActive(hit)
            setPinned(true)
          }
        }}
        onPointerLeave={(event) => {
          if (!pinned && event.pointerType !== "touch") setActive(null)
        }}
      >
        {empty || values.length ? (
          <svg
            viewBox={`0 0 ${plotWidth} 285`}
            className="w-full"
            style={{ height: 285 }}
            role="img"
            aria-label={
              empty
                ? "Gráfica de mediciones sin cota seleccionada"
                : `Gráfica de mediciones en ${unit}`
            }
          >
            {!empty && (
              <text
                x="18"
                y="22"
                fontSize="11"
                fill="currentColor"
                opacity=".6"
              >
                {unit}
              </text>
            )}
            {sameLimits && finite(first.lower) && finite(first.upper) && (
              <g>
                <rect
                  x="54"
                  y={y(first.upper)}
                  width={plotWidth - 108}
                  height={Math.max(1, y(first.lower) - y(first.upper))}
                  fill="#10b981"
                  opacity=".10"
                />
                {[first.lower, first.upper].map((value, index) => (
                  <g key={`${value}-${index}`}>
                    <line
                      x1="54"
                      x2={plotWidth - 54}
                      y1={y(value)}
                      y2={y(value)}
                      stroke="#059669"
                      strokeDasharray="4 4"
                    />
                    <text
                      x={plotWidth - 44}
                      y={y(value) + 4}
                      fontSize="10"
                      fill="#059669"
                    >
                      {fmt(value)}
                    </text>
                  </g>
                ))}
              </g>
            )}
            {[min, (min + max) / 2, max].map((value) => (
              <g key={value}>
                <line
                  x1="54"
                  x2={plotWidth - 54}
                  y1={y(value)}
                  y2={y(value)}
                  stroke="currentColor"
                  opacity=".08"
                />
                {!empty && (
                  <text
                    x="46"
                    y={y(value) + 4}
                    fontSize="11"
                    textAnchor="end"
                    fill="currentColor"
                    opacity=".6"
                  >
                    {fmt(value)}
                  </text>
                )}
              </g>
            ))}
            {lines.map(
              (line) =>
                visible.includes(line.name) && (
                  <g key={line.id ?? line.name}>
                    {line.points.map((point, index) => {
                      if (!point || !finite(point.value)) return null
                      const previous = line.points[index - 1]
                      return (
                        <g key={`${line.name}-${labels[index]}`}>
                          {index > 0 && previous && finite(previous.value) && (
                            <line
                              x1={x(index - 1)}
                              x2={x(index)}
                              y1={y(previous.value)}
                              y2={y(point.value)}
                              stroke={color(line.name)}
                              strokeWidth="2"
                              strokeDasharray={
                                point.prediction || previous.prediction
                                  ? "5 4"
                                  : undefined
                              }
                            />
                          )}
                          {!point.connectorOnly && (
                            <circle
                              cx={x(index)}
                              cy={y(point.value)}
                              r={
                                overlapping.some(
                                  (hit) =>
                                    hit.id ===
                                    `${line.id ?? line.name}-${index}`,
                                )
                                  ? 5
                                  : 4
                              }
                              fill={
                                point.prediction
                                  ? "var(--background)"
                                  : color(line.name)
                              }
                              stroke={color(line.name)}
                              strokeWidth="2"
                            />
                          )}
                        </g>
                      )
                    })}
                  </g>
                ),
            )}
            {labels.map((label, index) => (
              <text
                key={`${label}-${index}`}
                x={x(index)}
                y="263"
                textAnchor="middle"
                fontSize="12"
                fill="currentColor"
                opacity=".65"
              >
                {(compactLabels
                  ? label.replace(/^(intern\.)(.+)$/, "$1 · $2")
                  : label
                )
                  .split(" · ")
                  .map((text, line) => (
                    <tspan key={text} x={x(index)} dy={line ? 15 : 0}>
                      {text}
                    </tspan>
                  ))}
              </text>
            ))}
          </svg>
        ) : (
          <p className="flex min-h-64 items-center justify-center text-sm text-muted-foreground">
            Sin mediciones para esta selección.
          </p>
        )}
        {intervals && onInterval && (
          <fieldset className="pointer-events-none absolute inset-0">
            <legend className="sr-only">Tramos entre muestreos</legend>
            {intervals.map((interval) => (
              <button
                key={interval.id}
                type="button"
                aria-label={`Tramo ${labels[interval.from]} a ${labels[interval.to]}`}
                aria-pressed={selectedInterval === interval.id}
                className={cn(
                  "pointer-events-auto absolute cursor-pointer transition-colors hover:bg-neutral-500/10 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring",
                  selectedInterval === interval.id &&
                    "bg-neutral-500/20 hover:bg-neutral-500/20",
                )}
                style={{
                  left: x(interval.from),
                  top: 35,
                  width: x(interval.to) - x(interval.from),
                  height: 208,
                }}
                onFocus={() => {
                  setActive(null)
                  setPinned(false)
                }}
                onClick={() => {
                  setActive(null)
                  setPinned(false)
                  onInterval(interval.id)
                }}
              />
            ))}
          </fieldset>
        )}
        {hits.map((hit) => (
          <button
            key={hit.id}
            type="button"
            className="absolute size-4 rounded-full focus-visible:outline-2 focus-visible:outline-ring"
            style={{ left: hit.x - 8, top: hit.y - 8 }}
            aria-label={`Consultar ${hit.name.toUpperCase()} · ${labels[hit.index]}${hit.point.label ? ` · ${hit.point.label}` : ""}`}
            aria-describedby={
              active?.id === hit.id && !pinned ? tooltipId : undefined
            }
            aria-haspopup="dialog"
            aria-expanded={pinned && active?.id === hit.id}
            onFocus={() => {
              if (!pinned) setActive(hit)
            }}
            onBlur={() => {
              if (!pinned) setActive(null)
            }}
            onClick={() => {
              setActive(hit)
              setPinned(true)
            }}
          />
        ))}
        {active && overlapping.length > 0 && (
          <div
            id={tooltipId}
            data-plot-popover
            {...(pinned
              ? {
                  role: "dialog",
                  "aria-label": `Valores de ${labels[active.index]}`,
                }
              : { role: "tooltip" })}
            aria-live="polite"
            className={cn(
              "absolute z-10 rounded-md border bg-popover p-3 text-xs text-popover-foreground shadow-md",
              pinned ? "pointer-events-auto" : "pointer-events-none",
            )}
            style={{
              left: tooltipLeft,
              top: tooltipTop,
              width: tooltipWidth,
              maxHeight: 240,
              overflowY: "auto",
            }}
          >
            <div className="mb-2 flex items-center justify-between gap-2 font-medium">
              {labels[active.index]}
              {pinned && (
                <button
                  type="button"
                  aria-label="Cerrar valores"
                  className="rounded p-1 hover:bg-accent"
                  onClick={() => {
                    setPinned(false)
                    setActive(null)
                  }}
                >
                  <X className="size-3" />
                </button>
              )}
            </div>
            {overlapping.map((hit) => (
              <div
                key={hit.id}
                className={cn(
                  "flex items-center justify-between gap-3",
                  detailed ? "min-h-12 border-t py-1" : "h-6",
                )}
              >
                <span className="flex items-center gap-2">
                  <span
                    className="size-2 rounded-full"
                    style={{ backgroundColor: hit.color }}
                  />
                  <span>
                    {hit.name.toUpperCase()}
                    {hit.point.label && (
                      <span className="block text-muted-foreground">
                        {hit.point.label}
                      </span>
                    )}
                  </span>
                </span>
                <span className="text-right tabular-nums">
                  {pinned && onSource && hit.point.source?.file_id ? (
                    <button
                      type="button"
                      className="font-semibold text-primary underline underline-offset-2"
                      aria-label={`Ver origen ${hit.name.toUpperCase()} · ${fmt(hit.value)} ${unit}`}
                      onClick={() => onSource(hit.point, hit.name)}
                    >
                      {fmt(hit.value)} {unit}
                    </button>
                  ) : (
                    <b>
                      {fmt(hit.value)} {unit}
                    </b>
                  )}
                  {hit.point.change !== undefined && (
                    <span className="block text-muted-foreground">
                      Variación:{" "}
                      {hit.point.change == null
                        ? "—"
                        : `${hit.point.change > 0 ? "+" : hit.point.change < 0 ? "−" : ""}${fmt(Math.abs(hit.point.change))} ${unit}`}
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
      {!empty && (
        <fieldset className="flex flex-wrap items-center justify-center gap-2">
          <legend className="sr-only">Cavidades visibles</legend>
          {names.map((name) => (
            <Button
              key={name}
              type="button"
              variant="ghost"
              size="sm"
              aria-pressed={visible.includes(name)}
              onClick={() => toggle(name)}
              className={cn("gap-2", !visible.includes(name) && "opacity-40")}
            >
              <span
                className="size-2 rounded-full"
                style={{ backgroundColor: color(name) }}
              />
              {name.toUpperCase()}
            </Button>
          ))}
        </fieldset>
      )}
    </div>
  )
}
