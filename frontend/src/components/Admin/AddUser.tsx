import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { UsersService } from "@/client"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { useLoginMethods } from "@/hooks/useLoginMethods"
import { userError } from "./userError"

const formSchema = (microsoft: boolean) =>
  z
    .object({
      email: z
        .string()
        .trim()
        .pipe(
          z.email({
            message: "Introduce un correo válido",
          }),
        ),
      full_name: z.string().optional(),
      password: microsoft
        ? z.string()
        : z.string().min(1, { message: "Introduce una contraseña" }).min(8, {
            message: "La contraseña debe tener al menos 8 caracteres",
          }),
      confirm_password: microsoft
        ? z.string()
        : z.string().min(1, { message: "Confirma la contraseña" }),
      is_superuser: z.boolean(),
      is_active: z.boolean(),
    })
    .refine((data) => data.password === data.confirm_password, {
      message: "Las contraseñas no coinciden",
      path: ["confirm_password"],
    })

type FormData = z.infer<ReturnType<typeof formSchema>>

const AddUser = () => {
  const { data: methods } = useLoginMethods()
  const microsoft = methods?.microsoft === true
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema(microsoft)),
    mode: "onSubmit",
    reValidateMode: "onSubmit",
    criteriaMode: "all",
    defaultValues: {
      email: "",
      full_name: "",
      password: "",
      confirm_password: "",
      is_superuser: false,
      is_active: false,
    },
  })

  const mutation = useMutation({
    mutationFn: ({ confirm_password: _confirmation, ...data }: FormData) =>
      UsersService.createUser({
        requestBody: microsoft ? { email: data.email } : data,
      }),
    onSuccess: () => {
      showSuccessToast("Usuario creado")
      form.reset()
      setIsOpen(false)
    },
    onError: (error) => showErrorToast(userError(error)),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  const onSubmit = (data: FormData) => {
    mutation.mutate(data)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button disabled={!methods} className="h-11">
          <Plus />
          Añadir usuario
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md" closeLabel="Cerrar">
        <DialogHeader>
          <DialogTitle>Añadir usuario</DialogTitle>
          <DialogDescription>
            {microsoft
              ? "La persona entrará con su cuenta de Microsoft."
              : "Introduce los datos de la nueva cuenta."}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form noValidate onSubmit={form.handleSubmit(onSubmit)}>
            <div className="grid gap-4 py-4">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Correo <span className="text-destructive">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Correo"
                        type="email"
                        {...field}
                        required
                      />
                    </FormControl>
                    <FormMessage className="sr-only" />
                  </FormItem>
                )}
              />

              {!microsoft && (
                <>
                  <FormField
                    control={form.control}
                    name="full_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Nombre</FormLabel>
                        <FormControl>
                          <Input placeholder="Nombre" type="text" {...field} />
                        </FormControl>
                        <FormMessage className="sr-only" />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="password"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Contraseña <span className="text-destructive">*</span>
                        </FormLabel>
                        <FormControl>
                          <Input
                            placeholder="Contraseña"
                            type="password"
                            {...field}
                            required
                          />
                        </FormControl>
                        <FormMessage className="sr-only" />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="confirm_password"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Confirmar contraseña{" "}
                          <span className="text-destructive">*</span>
                        </FormLabel>
                        <FormControl>
                          <Input
                            placeholder="Contraseña"
                            type="password"
                            {...field}
                            required
                          />
                        </FormControl>
                        <FormMessage className="sr-only" />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="is_superuser"
                    render={({ field }) => (
                      <FormItem className="flex items-center gap-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                        <FormLabel className="font-normal">Admin</FormLabel>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="is_active"
                    render={({ field }) => (
                      <FormItem className="flex items-center gap-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                        <FormLabel className="font-normal">
                          Cuenta activa
                        </FormLabel>
                      </FormItem>
                    )}
                  />
                </>
              )}
            </div>

            <DialogFooter>
              <DialogClose asChild>
                <Button
                  type="button"
                  variant="outline"
                  disabled={mutation.isPending}
                >
                  Cancelar
                </Button>
              </DialogClose>
              <LoadingButton type="submit" loading={mutation.isPending}>
                Guardar
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

export default AddUser
