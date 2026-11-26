import { useContext } from "react"
import type { CorrectionText } from "@/client"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  CorrectionEditor,
  sameCorrection,
  sameInterval,
} from "./correctionTextDrafts"
import {
  type CorrectionInterval,
  intervalValues,
  proposalParagraphs,
} from "./correctionTimeline"
import { MeasurementPlot, type PlotLine } from "./MeasurementPlot"
import type { Evaluation } from "./measurementSelection"

export function CorrectionDetails({
  interval,
  cota,
  revision,
  correctionTexts,
  evaluation,
  cavities,
  visible,
  onVisible,
  actionId,
  onAction,
}: {
  interval: CorrectionInterval
  cota: string
  revision: string
  correctionTexts: CorrectionText[]
  evaluation: Evaluation
  cavities: string[]
  visible: string[]
  onVisible: (names: string[]) => void
  actionId?: string
  onAction: (id: string) => void
}) {
  const editor = useContext(CorrectionEditor)
  const scope = {
    cota,
    revision,
    before: interval.before,
    after: interval.after,
  }
  const stored = correctionTexts.filter((item) => sameInterval(item, scope))
  // A later import may add or retire a proposal after someone wrote about this interval.
  const proposals = [
    ...new Set([
      ...interval.actions.map((item) => item.id),
      ...stored.filter((item) => item.text).map((item) => item.action),
    ]),
  ]
  const defaultProposal = proposals.includes("") ? "" : (proposals[0] ?? "")
  const selected =
    actionId && proposals.includes(actionId) ? actionId : defaultProposal
  const action = interval.actions.find((item) => item.id === selected)
  const target = { ...scope, action: selected }
  const saved = stored.find((item) => item.action === selected)
  const imported = action
    ? interval.description || proposalParagraphs(action).join("\n\n")
    : ""
  const text = saved?.text ?? imported
  const draft = editor?.drafts.find((item) => sameCorrection(item, target))
  const values = cavities.map((cavity) => ({
    cavity,
    ...intervalValues(interval, evaluation, cavity),
  }))
  const hasPrediction = values.some(
    (item) => item.comparison?.prediction != null,
  )
  const differentBaseline = values.some(
    ({ cavity, before, comparison }) =>
      visible.includes(cavity) &&
      comparison?.prediction != null &&
      comparison.xls_before != null &&
      before?.value != null &&
      Math.abs(comparison.xls_before - before.value) > 0.0005,
  )
  const lines: PlotLine[] = values.flatMap(
    ({ cavity, before, after, comparison, measuredChange, expectedChange }) => [
      {
        id: `${cavity}-measured`,
        name: cavity,
        points: [
          before ? { ...before, label: "Original" } : null,
          after
            ? { ...after, label: "Cambio medido", change: measuredChange }
            : null,
        ],
      },
      {
        id: `${cavity}-prediction`,
        name: cavity,
        points: [
          before ? { ...before, connectorOnly: true } : null,
          comparison?.prediction != null
            ? {
                value: comparison.prediction,
                lower: comparison.lower,
                upper: comparison.upper,
                prediction: true,
                label: "Predicción",
                change: expectedChange,
              }
            : null,
        ],
      },
    ],
  )
  return (
    <section
      aria-label="Detalle del tramo"
      className="space-y-4 rounded-lg border p-4 sm:p-5"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <h3 className="font-medium">
          {interval.plans.length
            ? interval.plans
                .map((plan) => `Corrección ${plan.id} · ${plan.date}`)
                .join(" / ")
            : "Seguimiento posterior"}
        </h3>
        <span className="text-muted-foreground">{evaluation.label}</span>
      </div>
      <MeasurementPlot
        key={`${cota}-${evaluation.series.id}-${interval.id}`}
        labels={[`intern.${interval.before}`, `intern.${interval.after}`]}
        lines={lines}
        unit={evaluation.series.unit}
        visible={visible}
        onVisible={onVisible}
      />
      {hasPrediction ? (
        <p className="text-center text-xs text-muted-foreground">
          Línea continua y punto lleno: medición. Línea discontinua y punto
          vacío: predicción.
        </p>
      ) : (
        <p className="text-sm text-muted-foreground">
          Sin previsión documentada para esta evaluación.
        </p>
      )}
      {differentBaseline && (
        <p className="text-xs text-muted-foreground">
          La variación prevista usa la base del Excel, que difiere de la
          medición original. La variación medida usa las dos mediciones del
          tramo.
        </p>
      )}
      <div className="space-y-2 border-t pt-4 text-sm">
        {editor || action || text ? (
          <>
            <h4 className="font-medium">Cambio propuesto en el molde</h4>
            {editor ? (
              <Textarea
                aria-label="Cambio propuesto en el molde"
                value={draft?.text ?? text}
                onChange={(event) =>
                  editor.change({ ...target, text: event.target.value }, text)
                }
                disabled={editor.disabled}
              />
            ) : text ? (
              <p className="whitespace-pre-wrap [overflow-wrap:anywhere]">
                {text}
              </p>
            ) : (
              <p className="text-muted-foreground">Sin texto de corrección.</p>
            )}
            {action && (
              <p className="text-xs text-muted-foreground">
                Ejecución no confirmada en los documentos.
              </p>
            )}
          </>
        ) : (
          <p className="text-muted-foreground">
            No hay una acción vinculada a {cota}.
          </p>
        )}
      </div>
      {proposals.length > 1 && (
        <fieldset className="flex flex-wrap gap-2">
          <legend className="mb-2 text-xs text-muted-foreground">
            Propuestas del tramo
          </legend>
          {proposals.map((id) => (
            <Button
              key={id}
              type="button"
              size="sm"
              variant={selected === id ? "secondary" : "outline"}
              aria-pressed={selected === id}
              onClick={() => onAction(id)}
            >
              {id ? `Acción ${id}` : "Texto del tramo"}
            </Button>
          ))}
        </fieldset>
      )}
    </section>
  )
}
