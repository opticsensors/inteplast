import { FilterSelect } from "@/components/Common/FilterSelect"
import { Button } from "@/components/ui/button"
import {
  type CorrectionInterval,
  intervalValues,
  proposalParagraphs,
} from "./correctionTimeline"
import { fmt } from "./EvidenceElements"
import type { Evaluation } from "./measurementSelection"

const signed = (value: number | null | undefined) =>
  value == null
    ? "—"
    : `${value > 0 ? "+" : value < 0 ? "−" : ""}${fmt(Math.abs(value))}`

export function CorrectionDetails({
  interval,
  cota,
  evaluation,
  cavities,
  cavity,
  onCavity,
  actionId,
  onAction,
}: {
  interval: CorrectionInterval
  cota: string
  evaluation: Evaluation
  cavities: string[]
  cavity: string
  onCavity: (name: string) => void
  actionId?: string
  onAction: (id: string) => void
}) {
  const action =
    interval.actions.find((item) => item.id === actionId) ?? interval.actions[0]
  const { before, after, comparison, measuredChange, expectedChange } =
    intervalValues(interval, evaluation, cavity)
  const unit = evaluation.series.unit
  return (
    <section
      aria-label="Detalle del tramo"
      className="space-y-5 rounded-lg border p-4 sm:p-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">
            {interval.plans.length
              ? interval.plans
                  .map((plan) => `Corrección ${plan.id} · ${plan.date}`)
                  .join(" / ")
              : "Seguimiento posterior"}
          </h3>
          <p className="mt-1 text-xs text-muted-foreground">
            intern.{interval.before} → intern.{interval.after} ·{" "}
            {evaluation.label}
          </p>
        </div>
        <div className="w-32">
          <FilterSelect
            label="Cavidad"
            value={cavity}
            options={cavities.map((name) => ({
              value: name,
              label: name.toUpperCase(),
            }))}
            onChange={onCavity}
          />
        </div>
      </div>
      <div className="space-y-2 text-sm">
        {action ? (
          <>
            <h4 className="font-medium">Cambio propuesto en el molde</h4>
            {interval.description ? (
              <p>{interval.description}</p>
            ) : (
              proposalParagraphs(action).map((paragraph, index) => (
                <p key={`${index}-${paragraph}`}>{paragraph}</p>
              ))
            )}
            <p className="text-xs text-muted-foreground">
              Ejecución no confirmada en los documentos.
            </p>
          </>
        ) : (
          <p className="text-muted-foreground">
            {interval.plans.length
              ? `Existe un plan de corrección para este tramo, pero no hay una acción vinculada a ${cota}.`
              : "No hay una actuación documentada para este tramo. El cambio medido no permite atribuirlo a un retoque concreto."}
          </p>
        )}
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <section
          aria-label="Efecto previsto"
          className="space-y-1 rounded-md bg-muted/40 p-3"
        >
          <h4 className="text-xs text-muted-foreground">
            Efecto previsto · {cavity.toUpperCase()}
          </h4>
          {comparison?.prediction != null ? (
            <>
              <p className="text-lg font-semibold tabular-nums">
                {signed(expectedChange)} {unit}
              </p>
              <p className="text-sm tabular-nums">
                {fmt(comparison.xls_before)} → {fmt(comparison.prediction)}{" "}
                {unit}
              </p>
              {comparison.steps.length > 1 && (
                <p className="text-xs text-muted-foreground">
                  Pasos previstos:{" "}
                  {comparison.steps
                    .map((step) => `${signed(step.delta)} ${unit}`)
                    .join("; ")}
                </p>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              Sin previsión documentada para esta evaluación.
            </p>
          )}
        </section>
        <section
          aria-label="Cambio medido"
          className="space-y-1 rounded-md bg-muted/40 p-3"
        >
          <h4 className="text-xs text-muted-foreground">
            Cambio medido · {cavity.toUpperCase()}
          </h4>
          <p className="text-lg font-semibold tabular-nums">
            {signed(measuredChange)} {unit}
          </p>
          <p className="text-sm tabular-nums">
            {fmt(before?.value)} → {fmt(after?.value)} {unit}
          </p>
          {measuredChange == null && (
            <p className="text-xs text-muted-foreground">
              Falta una medición de este tramo.
            </p>
          )}
        </section>
      </div>
      {interval.actions.length > 1 && (
        <fieldset className="flex flex-wrap gap-2">
          <legend className="mb-2 text-xs text-muted-foreground">
            Propuestas del tramo
          </legend>
          {interval.actions.map((item) => (
            <Button
              key={item.id}
              type="button"
              size="sm"
              variant={action?.id === item.id ? "secondary" : "outline"}
              aria-pressed={action?.id === item.id}
              onClick={() => onAction(item.id)}
            >
              Acción {item.id}
            </Button>
          ))}
        </fieldset>
      )}
    </section>
  )
}
