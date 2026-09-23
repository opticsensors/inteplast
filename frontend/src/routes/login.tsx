import { zodResolver } from "@hookform/resolvers/zod"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { ArrowRight } from "lucide-react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import type { Body_login_login_access_token as AccessToken } from "@/client"
import { AuthLayout } from "@/components/Common/AuthLayout"
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
import { PasswordInput } from "@/components/ui/password-input"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"

const formSchema = z.object({
  username: z.email({ message: "Introduce un correo electrónico válido" }),
  password: z
    .string()
    .min(1, { message: "Introduce tu contraseña" })
    .min(8, { message: "La contraseña debe tener al menos 8 caracteres" }),
}) satisfies z.ZodType<AccessToken>

type FormData = z.infer<typeof formSchema>

export const Route = createFileRoute("/login")({
  component: Login,
  validateSearch: (search: Record<string, unknown>): { logout?: true } =>
    search.logout === true ? { logout: true } : {},
  beforeLoad: async ({ search }) => {
    // Route blockers finish pending saves before this loader is entered.
    if (search.logout) {
      localStorage.removeItem("access_token")
      throw redirect({ to: "/login", replace: true })
    }
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Iniciar sesión - INTEPLAST",
      },
    ],
  }),
})

function Login() {
  const { loginMutation } = useAuth()
  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onSubmit",
    reValidateMode: "onSubmit",
    criteriaMode: "all",
    defaultValues: {
      username: "",
      password: "",
    },
  })

  const onSubmit = (data: FormData) => {
    if (loginMutation.isPending) return
    loginMutation.mutate(data)
  }

  return (
    <AuthLayout contentClassName="max-w-md">
      <Form {...form}>
        <form
          noValidate
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-8"
        >
          <div className="space-y-2">
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Inicia sesión
            </h1>
            <p className="text-base text-muted-foreground">
              Ingresa tus datos para continuar.
            </p>
          </div>

          <div className="grid gap-5">
            <FormField
              control={form.control}
              name="username"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Correo electrónico</FormLabel>
                  <FormControl>
                    <Input
                      data-testid="email-input"
                      placeholder="nombre@empresa.com"
                      type="email"
                      autoComplete="username"
                      autoCapitalize="none"
                      spellCheck={false}
                      className="h-11 rounded-lg px-3.5 focus-visible:border-primary focus-visible:ring-primary/20"
                      {...field}
                    />
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
                  <FormLabel>Contraseña</FormLabel>
                  <FormControl>
                    <PasswordInput
                      data-testid="password-input"
                      placeholder="••••••••"
                      autoComplete="current-password"
                      className="h-11 rounded-lg pl-3.5 focus-visible:border-primary focus-visible:ring-primary/20"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage className="sr-only" />
                  <RouterLink
                    to="/recover-password"
                    className="justify-self-end text-sm font-medium text-primary underline underline-offset-4 hover:text-primary/80"
                  >
                    ¿Olvidaste tu contraseña?
                  </RouterLink>
                </FormItem>
              )}
            />

            <LoadingButton
              type="submit"
              loading={loginMutation.isPending}
              className="relative h-12 w-full rounded-lg px-12 text-base font-semibold"
            >
              Iniciar sesión
              {!loginMutation.isPending && (
                <ArrowRight
                  className="absolute right-4 size-5"
                  aria-hidden="true"
                />
              )}
            </LoadingButton>
          </div>

          <div className="border-t pt-6 text-center text-sm">
            <RouterLink
              to="/signup"
              className="font-medium text-primary underline underline-offset-4 hover:text-primary/80"
            >
              Crear una cuenta
            </RouterLink>
          </div>
        </form>
      </Form>
    </AuthLayout>
  )
}
