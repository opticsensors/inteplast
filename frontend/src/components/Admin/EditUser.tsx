import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Pencil } from "lucide-react"
import { useId, useState } from "react"

import { type UserAccessUpdate, type UserPublic, UsersService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { DropdownMenuItem } from "@/components/ui/dropdown-menu"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import { userError } from "./userError"

interface EditUserProps {
  user: UserPublic
  onSuccess: () => void
}

const EditUser = ({ user, onSuccess }: EditUserProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const [changes, setChanges] = useState<UserAccessUpdate>({})
  const roleId = useId()
  const statusId = useId()
  const isAdmin = changes.is_superuser ?? user.is_superuser
  const isActive = changes.is_active ?? user.is_active
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: () =>
      UsersService.updateUser({ userId: user.id, requestBody: changes }),
    onSuccess: () => {
      showSuccessToast("Usuario actualizado")
      setIsOpen(false)
      onSuccess()
    },
    onError: (error) => showErrorToast(userError(error)),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuItem
        onSelect={(event) => {
          event.preventDefault()
          setChanges({})
          setIsOpen(true)
        }}
      >
        <Pencil />
        Editar usuario
      </DropdownMenuItem>
      <DialogContent className="sm:max-w-md" closeLabel="Cerrar">
        <DialogHeader>
          <DialogTitle>Editar usuario</DialogTitle>
          <DialogDescription className="break-all">
            {user.email}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor={roleId}>Rol</Label>
            <Select
              value={isAdmin ? "admin" : "user"}
              onValueChange={(role) =>
                setChanges((prev) => ({
                  ...prev,
                  is_superuser: role === "admin",
                }))
              }
              disabled={mutation.isPending}
            >
              <SelectTrigger id={roleId} className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="user">Usuario</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor={statusId}>Estado</Label>
            <Select
              value={isActive ? "active" : "inactive"}
              onValueChange={(status) =>
                setChanges((prev) => ({
                  ...prev,
                  is_active: status === "active",
                }))
              }
              disabled={mutation.isPending}
            >
              <SelectTrigger id={statusId} className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Activo</SelectItem>
                <SelectItem value="inactive">Inactivo</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline" disabled={mutation.isPending}>
              Cancelar
            </Button>
          </DialogClose>
          <LoadingButton
            onClick={() => mutation.mutate()}
            disabled={
              isAdmin === user.is_superuser && isActive === user.is_active
            }
            loading={mutation.isPending}
          >
            Guardar
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default EditUser
