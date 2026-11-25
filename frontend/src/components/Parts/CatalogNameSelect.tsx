import { queryOptions, useQuery, useQueryClient } from "@tanstack/react-query"

import { type CatalogNamePublic, CatalogService } from "@/client"
import { SearchSelect } from "@/components/Common/SearchSelect"

const catalogs = {
  families: {
    label: "Familia",
    empty: "Sin familia",
    add: "Añadir familia",
    read: CatalogService.readFamilies,
    create: CatalogService.createFamily,
  },
  customers: {
    label: "Cliente",
    empty: "Sin cliente",
    add: "Añadir cliente",
    read: CatalogService.readCustomers,
    create: CatalogService.createCustomer,
  },
  materials: {
    label: "Material",
    empty: "Sin material",
    add: "Añadir material",
    read: CatalogService.readMaterials,
    create: CatalogService.createMaterial,
  },
}

export type CatalogNameKind = keyof typeof catalogs

export const catalogNamesQueryOptions = (kind: CatalogNameKind) =>
  queryOptions({
    queryKey: ["catalog-names", kind],
    queryFn: () => catalogs[kind].read(),
    staleTime: 60_000,
  })

/**
 * Familia, cliente o material de una pieza, con buscador y alta en la lista compartida.
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
  const catalog = catalogs[kind]
  const create = async (name: string) => {
    const created = await catalog.create({ requestBody: { name } })
    await client.invalidateQueries({ queryKey: ["catalog-names", kind] })
    return created.id
  }
  return (
    <SearchSelect
      showLabel
      label={catalog.label}
      value={value}
      placeholder={catalog.empty}
      emptyLabel={catalog.empty}
      selectedLabel={selected?.id === value ? selected?.name : undefined}
      options={(names.data?.data ?? []).map((item) => ({
        value: item.id,
        label: item.name,
      }))}
      onChange={(next) => onChange(next ?? null)}
      onCreate={create}
      createLabel={catalog.add}
      disabled={disabled}
    />
  )
}
