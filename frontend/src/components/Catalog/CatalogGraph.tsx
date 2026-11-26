import { useQuery, useQueryClient } from "@tanstack/react-query"
import ForceGraph, {
  type ForceGraphInstance,
  type GraphData,
  type LinkObject,
  type NodeObject,
} from "force-graph"
import { useEffect, useMemo, useRef, useState } from "react"

import {
  type CatalogGraph as CatalogGraphData,
  CatalogService,
  type GraphNode,
} from "@/client"
import { partName } from "@/components/Features/parts"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { coverQuery } from "@/hooks/useCatalogCover"
import {
  absoluteFileUrl,
  fileAccessQueryOptions,
  fileErrorMessage,
} from "@/hooks/useFileAccess"

export type CatalogGraphRequest = {
  q: string
  kind: "all" | "part" | "feature"
  partId: string | null
  featureId: string | null
  familyId: string | null
  customerId: string | null
}

type Node = GraphNode & { x?: number; y?: number; width?: number }
type Link = { source: string | Node; target: string | Node; kind: string }

const PART_RADIUS = 9

/** Colours of the web theme, read again whenever light or dark changes. */
function themeColors() {
  const style = getComputedStyle(document.documentElement)
  const read = (name: string, fallback: string) =>
    style.getPropertyValue(name).trim() || fallback
  return {
    background: read("--card", "#ffffff"),
    text: read("--foreground", "#111111"),
    muted: read("--muted-foreground", "#777777"),
    feature: read("--primary", "#2a9d8f"),
    featureText: read("--primary-foreground", "#ffffff"),
    // Light pills with dark text: readable on both themes.
    family: "#fbbf24",
    customer: "#f9a8d4",
    part: "rgb(14 165 233)",
  }
}

function useThemeColors() {
  const [colors, setColors] = useState(themeColors)
  useEffect(() => {
    const update = () => setColors(themeColors())
    const observer = new MutationObserver(update)
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class", "style", "data-theme"],
    })
    const media = window.matchMedia("(prefers-color-scheme: dark)")
    media.addEventListener("change", update)
    return () => {
      observer.disconnect()
      media.removeEventListener("change", update)
    }
  }, [])
  return colors
}

/** The saved CAD capture of each piece; the graph never asks for a new one. */
function usePartImages(nodes: GraphNode[] | undefined) {
  const client = useQueryClient()
  const [images, setImages] = useState<Record<string, HTMLImageElement>>({})
  useEffect(() => {
    let cancelled = false
    const queue = (nodes ?? []).filter(
      (node) => node.deferred_cover_part_id || node.image,
    )
    setImages({})
    async function load() {
      for (let node = queue.shift(); node && !cancelled; node = queue.shift()) {
        try {
          const cover = node.deferred_cover_part_id
            ? await client.fetchQuery(coverQuery(node.deferred_cover_part_id))
            : undefined
          const file =
            cover?.face_colors?.images.part ?? cover?.image ?? node.image
          if (!file || cancelled) continue
          const access = await client.fetchQuery(
            fileAccessQueryOptions(file.id),
          )
          if (cancelled) return
          const image = new Image()
          image.src = absoluteFileUrl(access.url)
          await image.decode()
          const id = node.id
          if (!cancelled) setImages((all) => ({ ...all, [id]: image }))
        } catch {
          // The piece keeps its code when its capture cannot be read.
        }
      }
    }
    const workers = Math.min(4, queue.length)
    for (let i = 0; i < workers; i++) void load()
    return () => {
      cancelled = true
    }
  }, [nodes, client])
  return images
}

/** Text shown as HTML by force-graph's tooltip must never become markup. */
export const escapeHtml = (text: string) =>
  text.replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ] as string,
  )

export const graphCountText = (graph: CatalogGraphData) =>
  graph.truncated
    ? `Mostrando ${graph.nodes.length.toLocaleString("es-ES")} de ${graph.total.toLocaleString("es-ES")}: filtra para ver el resto`
    : null

/**
 * Pieces, features and, if switched on, families and customers: the same results as the
 * list. Pieces are circles with their CAD capture; features carry their name. Clicking
 * a piece or a feature opens it; a family or a customer filters the catalogue.
 * It is not keyboard navigable: the list and the grid are the accessible views.
 */
export default function CatalogGraph({
  request,
  onOpen,
  onFilter,
}: {
  request: CatalogGraphRequest
  onOpen: (node: GraphNode) => void
  onFilter: (kind: "family" | "customer", id: string) => void
}) {
  const [families, setFamilies] = useState(false)
  const [customers, setCustomers] = useState(false)
  const query = useQuery({
    queryKey: ["features", "catalog-graph", request],
    queryFn: () =>
      CatalogService.readCatalogGraph({
        deferCovers: true,
        q: request.q,
        kind: request.kind,
        partId: request.partId,
        featureId: request.featureId,
        familyId: request.familyId,
        customerId: request.customerId,
      }),
  })
  const colors = useThemeColors()
  const data = useMemo(() => {
    const visible = (node: GraphNode) =>
      (node.kind !== "family" || families) &&
      (node.kind !== "customer" || customers)
    const nodes: Node[] = (query.data?.nodes ?? [])
      .filter(visible)
      .map((node) => ({ ...node }))
    const ids = new Set(nodes.map((node) => node.id))
    const links: Link[] = (query.data?.links ?? [])
      .filter((link) => ids.has(link.source) && ids.has(link.target))
      .map((link) => ({ ...link }))
    return { nodes, links }
  }, [query.data, families, customers])
  const images = usePartImages(query.data?.nodes)
  const container = useRef<HTMLDivElement>(null)
  const graph = useRef<ForceGraphInstance | null>(null)
  // The data whose layout has settled: positions are final and nodes can be clicked.
  const [settled, setSettled] = useState<object | null>(null)
  const viewKey = JSON.stringify([request, families, customers])
  const fittedView = useRef<string | null>(null)
  const latest = useRef({ colors, images, onOpen, onFilter, data, viewKey })
  latest.current = { colors, images, onOpen, onFilter, data, viewKey }

  useEffect(() => {
    const element = container.current
    if (!element) return
    const asNode = (node: NodeObject) => node as Node
    const instance = ForceGraph()(element)
      .width(element.clientWidth)
      .height(element.clientHeight)
      .nodeId("id")
      .nodeLabel((object) => {
        const node = asNode(object)
        const name =
          node.kind === "part"
            ? partName({ code: node.label, name: node.name })
            : ""
        // force-graph writes this into the tooltip as HTML: names are user text.
        return escapeHtml(name ? `${node.label} ${name}` : node.label)
      })
      .nodeCanvasObject((object, ctx) => {
        const node = asNode(object)
        const { colors: theme, images: pictures } = latest.current
        const x = node.x ?? 0
        const y = node.y ?? 0
        if (node.kind === "part") {
          ctx.save()
          ctx.beginPath()
          ctx.arc(x, y, PART_RADIUS, 0, 2 * Math.PI)
          ctx.fillStyle = theme.background
          ctx.fill()
          const picture = pictures[node.id]
          if (picture) {
            ctx.clip()
            const size = PART_RADIUS * 2
            ctx.drawImage(picture, x - PART_RADIUS, y - PART_RADIUS, size, size)
          }
          ctx.restore()
          ctx.beginPath()
          ctx.arc(x, y, PART_RADIUS, 0, 2 * Math.PI)
          ctx.lineWidth = 1.2
          ctx.strokeStyle = theme.part
          ctx.stroke()
          // Without a capture the code goes inside the circle; with one, below it.
          ctx.fillStyle = theme.text
          ctx.textAlign = "center"
          ctx.font = "600 4px system-ui, sans-serif"
          ctx.textBaseline = picture ? "top" : "middle"
          ctx.fillText(node.label, x, picture ? y + PART_RADIUS + 1.5 : y)
          return
        }
        ctx.font = "600 4.5px system-ui, sans-serif"
        node.width = ctx.measureText(node.label).width + 8
        ctx.fillStyle =
          node.kind === "feature"
            ? theme.feature
            : node.kind === "family"
              ? theme.family
              : theme.customer
        ctx.beginPath()
        ctx.roundRect(x - node.width / 2, y - 5, node.width, 10, 5)
        ctx.fill()
        ctx.fillStyle = node.kind === "feature" ? theme.featureText : "#111"
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        ctx.fillText(node.label, x, y + 0.3)
      })
      .nodePointerAreaPaint((object, color, ctx) => {
        const node = asNode(object)
        ctx.fillStyle = color
        ctx.beginPath()
        if (node.kind === "part")
          ctx.arc(node.x ?? 0, node.y ?? 0, PART_RADIUS, 0, 2 * Math.PI)
        else {
          const width = node.width ?? 30
          ctx.rect((node.x ?? 0) - width / 2, (node.y ?? 0) - 5, width, 10)
        }
        ctx.fill()
      })
      .linkColor(() => latest.current.colors.muted)
      .linkWidth(1.2)
      .linkLineDash((link: LinkObject) =>
        (link as Link).kind === "feature" ? null : [2, 2],
      )
      .onNodeHover((node) => {
        element.style.cursor = node ? "pointer" : ""
      })
      .onNodeClick((object) => {
        const node = asNode(object)
        if (node.kind === "family" || node.kind === "customer")
          latest.current.onFilter(node.kind, node.ref_id)
        else latest.current.onOpen(node)
      })
      .onNodeDragEnd((node) => {
        node.fx = node.x
        node.fy = node.y
      })
      // A few nodes must not fill the screen when the graph fits them.
      .maxZoom(4)
      .warmupTicks(100)
      .cooldownTicks(24)
      .onEngineTick(() => {
        const { data, viewKey } = latest.current
        if (
          data.nodes.length &&
          fittedView.current !== viewKey &&
          instance.graphData().nodes === data.nodes
        ) {
          fittedView.current = viewKey
          instance.zoomToFit(0, 40)
        }
      })
      .onEngineStop(() => setSettled(latest.current.data))
    instance.d3Force("charge")?.strength(-160)
    instance.d3Force("link")?.distance(55).strength(0.55)
    graph.current = instance
    const keepView = () => {
      fittedView.current = latest.current.viewKey
    }
    const captureWheel = (event: WheelEvent) => {
      keepView()
      // d3 handles the zoom but allows native scrolling at its scale limits.
      event.preventDefault()
    }
    const frame = element.parentElement!
    frame.addEventListener("wheel", captureWheel, {
      capture: true,
      passive: false,
    })
    element.addEventListener("pointerdown", keepView, true)
    // Tests reach the real node positions through the element; there is no other API.
    Object.defineProperty(element, "catalogGraph", {
      value: instance,
      configurable: true,
    })
    const resize = new ResizeObserver(() =>
      instance.width(element.clientWidth).height(element.clientHeight),
    )
    resize.observe(element)
    return () => {
      frame.removeEventListener("wheel", captureWheel, true)
      element.removeEventListener("pointerdown", keepView, true)
      resize.disconnect()
      instance._destructor()
      graph.current = null
    }
  }, [])

  useEffect(() => {
    const instance = graph.current
    if (!instance) return
    const pinned = new Map(
      instance
        .graphData()
        .nodes.filter((n) => n.fx != null && n.fy != null)
        .map((n) => [n.id, n]),
    )
    for (const node of data.nodes) {
      const previous = pinned.get(node.id)
      if (previous)
        Object.assign(node, {
          x: previous.fx,
          y: previous.fy,
          fx: previous.fx,
          fy: previous.fy,
        })
    }
    instance.graphData(data as unknown as GraphData)
  }, [data])

  useEffect(() => {
    const instance = graph.current
    if (!instance) return
    instance.backgroundColor(colors.background)
    container.current!.dataset.background = colors.background
    // Nodes are drawn with the theme too: repaint them without moving anything.
    instance.nodeRelSize(instance.nodeRelSize())
  }, [colors])

  useEffect(() => {
    const instance = graph.current
    // A capture that arrives only changes the drawing: repaint without moving nodes.
    if (instance && Object.keys(images).length)
      instance.nodeRelSize(instance.nodeRelSize())
  }, [images])

  const notice = query.data ? graphCountText(query.data) : null
  return (
    <section aria-label="Grafo del catálogo" className="space-y-3">
      {notice && (
        <output className="block text-sm font-medium text-amber-600">
          {notice}
        </output>
      )}
      {query.error && (
        <p role="alert" className="text-sm text-destructive">
          {fileErrorMessage(query.error)}
        </p>
      )}
      <div className="relative h-[70vh] min-h-96 overflow-hidden rounded-lg border bg-card">
        {query.isPending && <Skeleton className="absolute inset-0" />}
        {query.data && !query.data.nodes.length && (
          <p className="absolute inset-0 flex items-center justify-center text-muted-foreground">
            No hay resultados
          </p>
        )}
        {/* Legend over the graph, top left: one switch per line. */}
        <fieldset
          aria-label="Mostrar en el grafo"
          className="absolute top-3 left-3 z-10 space-y-2 rounded-md border bg-card/90 px-3 py-2.5 text-sm shadow-sm backdrop-blur-sm"
        >
          {(
            [
              ["graph-families", "Familias", families, setFamilies, "#fbbf24"],
              [
                "graph-customers",
                "Clientes",
                customers,
                setCustomers,
                "#f9a8d4",
              ],
            ] as const
          ).map(([id, label, checked, set, color]) => (
            <div key={id} className="flex items-center gap-2">
              <Checkbox
                id={id}
                checked={checked}
                onCheckedChange={(value) => set(value === true)}
              />
              <span
                aria-hidden
                className="size-2.5 rounded-full"
                style={{ backgroundColor: color }}
              />
              <Label htmlFor={id} className="font-normal">
                {label}
              </Label>
            </div>
          ))}
        </fieldset>
        <div
          ref={container}
          // Out of the flow: the canvas has a fixed pixel width and must not widen the page.
          className="absolute inset-0"
          data-testid="catalog-graph"
          data-nodes={data.nodes.length}
          data-ready={settled === data}
        />
      </div>
    </section>
  )
}
