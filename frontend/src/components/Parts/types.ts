export type EvidenceSource = { file_id: string; path: string; locator: string }
export type Measurement = {
  value: number | null
  lower: number | null
  upper: number | null
  status: string
  source: EvidenceSource
  corrected?: boolean
  original_value?: number
}
export type Comparison = {
  label: string
  before: Measurement | null
  after: Measurement | null
  prediction: number | null
  prediction_status: string
  lower: number | null
  upper: number | null
  xls_before: number | null
  steps: { delta: number | null; value: number | null; cells: string }[]
  source: EvidenceSource
  history: (Measurement | null)[]
}
export type Case = {
  title: string
  caption: string
  description?: string
  correction: string
  actions: string[]
  note: string
  variants: string[]
  comparisons: Record<
    string,
    Record<string, { items: Comparison[]; warnings: string[] }>
  >
}
export type Action = {
  id: string
  plan?: string
  title?: string
  features?: string[]
  paragraphs: string[]
  images: { url: string; label: string }[]
  marker?: string
  source: EvidenceSource
}
export type Series = {
  element?: string | null
  evaluation?: string | null
  id: string
  label: string
  unit: string
  block?: string
  idx?: number
  records: Record<string, Record<string, Measurement>>
}
export type Entry = {
  revision?: string
  id: string
  numbers: string[]
  kind: string
  title: string
  series: Series[]
  actions: string[]
  reviewed_case: string | null
}
export type Profile = {
  sample: string
  cavity: string
  element: string
  crop_image: string
  source: EvidenceSource
  excess: number | null
  tol_inf: number
  tol_sup: number
  errors: string[]
}
export type Study = {
  cases: Record<string, Case>
  corrections: Record<string, { before: string; after: string; date: string }>
  actions: Record<string, Action>
  action_index: Record<string, Action>
  samples: string[]
  cavities: string[]
  csv_count: number
  measurement_revision: string
  profiles: Profile[]
  catalog: { entries: Entry[]; row_count: number }
  support: {
    sample: string
    cavity: string
    kind: string
    source: EvidenceSource
    points?: number
    subset_verified?: boolean
  }[]
}
