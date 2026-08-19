import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus } from "lucide-react"
import { useState } from "react"

import { PartsService } from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { partLabel } from "./parts"
import { partsQueryOptions } from "./queries"

/** Radix no admite un SelectItem con value vacio: hacen falta centinelas.
 *  El value "" del Select si vale, y es lo que enseña el placeholder. */
const NONE = "none"
const NEW = "new"

interface PartSelectProps {
  value: string | null
  onChange: (partId: string | null) => void
  /** Ofrecer "sin pieza". En el adjunto si; al declarar una pieza no. */
  allowEmpty?: boolean
  placeholder?: string
}

/**
 * Desplegable de piezas existentes con alta al vuelo. Sustituye al texto libre
 * de antes: el codigo de pieza es la clave con la que se agrupa todo, y escrito
 * a mano acababa con "3212 Pump Housing" y "3212 lote 315346" como dos piezas.
 */
export function PartSelect({
  value,
  onChange,
  allowEmpty = false,
  placeholder = "Elige una pieza",
}: PartSelectProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { data } = useQuery(partsQueryOptions())
  const [creating, setCreating] = useState(false)
  const [code, setCode] = useState("")
  const [name, setName] = useState("")

  const parts = data?.data ?? []

  const mutation = useMutation({
    mutationFn: () =>
      PartsService.createPart({
        requestBody: { code: code.trim(), name: name.trim() || null },
      }),
    onSuccess: (part) => {
      showSuccessToast("Pieza creada")
      setCreating(false)
      setCode("")
      setName("")
      onChange(part.id)
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["parts"] })
      // Los desplegables de filtrado del dashboard salen de /features/filters
      queryClient.invalidateQueries({ queryKey: ["features"] })
    },
  })

  if (creating) {
    return (
      <div className="space-y-2 rounded-md border p-2">
        <div className="grid grid-cols-3 gap-2">
          <Input
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder="3212"
            aria-label="Codigo de la pieza"
          />
          <Input
            className="col-span-2"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Pump Housing"
            aria-label="Nombre de la pieza"
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setCreating(false)}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={!code.trim() || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            Crear pieza
          </Button>
        </div>
      </div>
    )
  }

  return (
    <Select
      value={value ?? ""}
      onValueChange={(next) => {
        if (next === NEW) {
          setCreating(true)
          return
        }
        onChange(next === NONE ? null : next)
      }}
    >
      <SelectTrigger className="w-full">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {allowEmpty && <SelectItem value={NONE}>Sin pieza</SelectItem>}
        {parts.map((part) => (
          <SelectItem key={part.id} value={part.id}>
            {partLabel(part)}
          </SelectItem>
        ))}
        <SelectItem value={NEW}>
          <Plus className="size-3.5" />
          Nueva pieza...
        </SelectItem>
      </SelectContent>
    </Select>
  )
}
