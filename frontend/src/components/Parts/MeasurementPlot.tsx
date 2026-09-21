import { useEffect, useId, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { fmt } from "./EvidenceElements"
import type { Measurement } from "./types"

export type PlotPoint = Partial<Measurement> & {
  value: number | null
  prediction?: boolean
}
export type PlotLine = {
  name: string
  points: (PlotPoint | null | undefined)[]
}
type Hit = {
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
}: {
  labels: string[]
  lines: PlotLine[]
  visible: string[]
  onVisible: (names: string[]) => void
  unit?: string
  intervals?: { id: string; from: number; to: number }[]
  selectedInterval?: string
  onInterval?: (id: string) => void
}) {
  const tooltipId = useId()
  const [active, setActive] = useState<Hit | null>(null)
  const plot = useRef<HTMLDivElement>(null)
  const [plotWidth, setPlotWidth] = useState(740)
  useEffect(() => {
    const node = plot.current
    if (!node) return
    const observer = new ResizeObserver(() => {
      setPlotWidth(Math.max(1, node.clientWidth))
      setActive(null)
    })
    observer.observe(node)
    const dismiss = (event: PointerEvent) => {
      if (!node.contains(event.target as Node)) setActive(null)
    }
    document.addEventListener("pointerdown", dismiss)
    return () => {
      observer.disconnect()
      document.removeEventListener("pointerdown", dismiss)
    }
  }, [])
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
  const y = (value: number) => 235 - ((value - min) / (max - min)) * 190
  const hits: Hit[] = lines.flatMap((line, lineIndex) =>
    visible.includes(line.name)
      ? line.points.flatMap((point, index) =>
          point && finite(point.value)
            ? [
                {
                  name: line.name,
                  index,
                  value: point.value,
                  x: x(index),
                  y: y(point.value),
                  color: colors[lineIndex % colors.length],
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
  const tooltipWidth = Math.min(184, plotWidth - 16)
  const tooltipHeight = 44 + overlapping.length * 24
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
    onVisible(
      visible.includes(name)
        ? visible.filter((item) => item !== name)
        : [...visible, name],
    )
    setActive(null)
  }
  return (
    <div className="min-w-0 space-y-3">
      <div
        ref={plot}
        className="relative"
        onPointerMove={(event) => {
          if (event.pointerType !== "touch")
            setActive(hitAt(event.clientX, event.clientY))
        }}
        onPointerDown={(event) => {
          if (event.pointerType === "touch")
            setActive(hitAt(event.clientX, event.clientY, 16))
        }}
        onPointerLeave={(event) => {
          if (event.pointerType !== "touch") setActive(null)
        }}
      >
        {values.length ? (
          <svg
            viewBox={`0 0 ${plotWidth} 285`}
            className="w-full"
            style={{ height: 285 }}
            role="img"
            aria-label={`Gráfica de mediciones en ${unit}`}
          >
            <text x="18" y="22" fontSize="11" fill="currentColor" opacity=".6">
              {unit}
            </text>
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
              </g>
            ))}
            {lines.map(
              (line, lineIndex) =>
                visible.includes(line.name) && (
                  <g key={line.name}>
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
                              stroke={colors[lineIndex % colors.length]}
                              strokeWidth="2"
                              strokeDasharray={
                                point.prediction || previous.prediction
                                  ? "5 4"
                                  : undefined
                              }
                            />
                          )}
                          <circle
                            cx={x(index)}
                            cy={y(point.value)}
                            r={
                              overlapping.some(
                                (hit) =>
                                  hit.name === line.name && hit.index === index,
                              )
                                ? 5
                                : 4
                            }
                            fill={
                              point.prediction
                                ? "var(--background)"
                                : colors[lineIndex % colors.length]
                            }
                            stroke={colors[lineIndex % colors.length]}
                            strokeWidth="2"
                          />
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
                {label.split(" · ").map((text, line) => (
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
                onFocus={() => setActive(null)}
                onClick={() => {
                  setActive(null)
                  onInterval(interval.id)
                }}
              />
            ))}
          </fieldset>
        )}
        {hits.map((hit) => (
          <button
            key={`${hit.name}-${hit.index}`}
            type="button"
            className="absolute size-4 rounded-full focus-visible:outline-2 focus-visible:outline-ring"
            style={{ left: hit.x - 8, top: hit.y - 8 }}
            aria-label={`Consultar ${hit.name.toUpperCase()} · ${labels[hit.index]}`}
            aria-describedby={
              active?.index === hit.index && active.name === hit.name
                ? tooltipId
                : undefined
            }
            onFocus={() => setActive(hit)}
            onBlur={() => setActive(null)}
            onClick={() => setActive(hit)}
            onKeyDown={(event) => {
              if (event.key === "Escape") setActive(null)
            }}
          />
        ))}
        {active && overlapping.length > 0 && (
          <div
            id={tooltipId}
            role="tooltip"
            aria-live="polite"
            className="pointer-events-none absolute z-10 rounded-md border bg-popover p-3 text-xs text-popover-foreground shadow-md"
            style={{ left: tooltipLeft, top: tooltipTop, width: tooltipWidth }}
          >
            <div className="mb-2 font-medium">{labels[active.index]}</div>
            {overlapping.map((hit) => (
              <div
                key={hit.name}
                className="flex h-6 items-center justify-between gap-3"
              >
                <span className="flex items-center gap-2">
                  <span
                    className="size-2 rounded-full"
                    style={{ backgroundColor: hit.color }}
                  />
                  {hit.name.toUpperCase()}
                </span>
                <b className="tabular-nums">
                  {fmt(hit.value)} {unit}
                </b>
              </div>
            ))}
          </div>
        )}
      </div>
      <fieldset className="flex flex-wrap items-center justify-center gap-2">
        <legend className="sr-only">Cavidades visibles</legend>
        {lines.map((line, index) => (
          <Button
            key={line.name}
            type="button"
            variant="ghost"
            size="sm"
            aria-pressed={visible.includes(line.name)}
            onClick={() => toggle(line.name)}
            className={cn(
              "gap-2",
              !visible.includes(line.name) && "opacity-40",
            )}
          >
            <span
              className="size-2 rounded-full"
              style={{ backgroundColor: colors[index % colors.length] }}
            />
            {line.name.toUpperCase()}
          </Button>
        ))}
      </fieldset>
    </div>
  )
}
