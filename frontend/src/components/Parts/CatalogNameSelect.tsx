import { queryOptions, useQuery, useQueryClient } from "@tanstack/react-query"

import { type CatalogNamePublic, CatalogService } from "@/client"
import { SearchSelect } from "@/components/Common/SearchSelect"

export type CatalogNameKind = "families" | "customers"

const LABELS: Record<
  CatalogNameKind,
  { label: string; placeholder: string; empty: string }
> = {
  families: {
    label: "Familia",
    placeholder: "Sin familia",
    empty: "Sin familia",
  },
  customers: {
    label: "Cliente",
    placeholder: "Sin cliente",
    empty: "Sin cliente",
  },
}

export const catalogNamesQueryOptions = (kind: CatalogNameKind) =>
  queryOptions({
    queryKey: ["catalog-names", kind],
    queryFn: () =>
      kind === "families"
        ? CatalogService.readFamilies()
        : CatalogService.readCustomers(),
    staleTime: 60_000,
  })

/**
 * Familia o cliente de una pieza: lista compartida con buscador y «Añadir» al final.
 * Añadir un nombre que ya existe, con otras mayúsculas o espacios, elige el existente.
 */
export function CatalogNameSelect({
  kind,
  value,
  selected,
  onChange,
  disabled,
}: {
  kind: CatalogNameKind
  value: string | null
  /** The saved entry, so that its name shows before the list arrives. */
  selected?: CatalogNamePublic | null
  onChange: (value: string | null) => void
  disabled?: boolean
}) {
  const client = useQueryClient()
  const names = useQuery(catalogNamesQueryOptions(kind))
  const text = LABELS[kind]
  const create = async (name: string) => {
    const requestBody = { name }
    const created =
      kind === "families"
        ? await CatalogService.createFamily({ requestBody })
        : await CatalogService.createCustomer({ requestBody })
    await client.invalidateQueries({ queryKey: ["catalog-names", kind] })
    return created.id
  }
  return (
    <SearchSelect
      showLabel
      label={text.label}
      value={value}
      placeholder={text.placeholder}
      emptyLabel={text.empty}
      selectedLabel={selected?.id === value ? selected?.name : undefined}
      options={(names.data?.data ?? []).map((item) => ({
        value: item.id,
        label: item.name,
      }))}
      onChange={(next) => onChange(next ?? null)}
      onCreate={create}
      createLabel={kind === "families" ? "Añadir familia" : "Añadir cliente"}
      disabled={disabled}
    />
  )
}
