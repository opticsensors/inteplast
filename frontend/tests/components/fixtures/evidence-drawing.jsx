export default function PdfViewer({ focus }) {
  window.review.drawingFocus = focus
  return (
    <section
      aria-label="Plano de prueba"
      className="flex h-96 items-center justify-center rounded-lg border bg-muted/30"
    >
      Plano · {focus?.label ?? "Completo"}
    </section>
  )
}
