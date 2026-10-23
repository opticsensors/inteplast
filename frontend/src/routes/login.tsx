import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
  useNavigate,
} from "@tanstack/react-router"
import { ArrowRight, Loader2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  type Body_login_login_access_token as AccessToken,
  LoginService,
  type Token,
} from "@/client"
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
import { useLoginMethods } from "@/hooks/useLoginMethods"
import { handleError } from "@/utils"

const formSchema = z.object({
  username: z.email({ message: "Introduce un correo electrónico válido" }),
  password: z
    .string()
    .min(1, { message: "Introduce tu contraseña" })
    .min(8, { message: "La contraseña debe tener al menos 8 caracteres" }),
}) satisfies z.ZodType<AccessToken>

type FormData = z.infer<typeof formSchema>

type LoginSearch = {
  logout?: true
  /** One-time ticket when Microsoft returned to the API. */
  microsoft?: string
  microsoft_error?: string
}

export const Route = createFileRoute("/login")({
  component: Login,
  validateSearch: (search: Record<string, unknown>): LoginSearch => ({
    ...(search.logout === true ? { logout: true as const } : {}),
    ...(typeof search.microsoft === "string"
      ? { microsoft: search.microsoft }
      : {}),
    ...(typeof search.microsoft_error === "string"
      ? { microsoft_error: search.microsoft_error }
      : {}),
  }),
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
  const { data: methods, isPending } = useLoginMethods()

  return (
    <AuthLayout contentClassName="max-w-md">
      <div className="flex flex-col gap-8">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Inicia sesión
          </h1>
          <p className="text-base text-muted-foreground">
            {methods?.microsoft
              ? "Entra con tu cuenta de la empresa."
              : "Ingresa tus datos para continuar."}
          </p>
        </div>
        {isPending ? (
          <Loader2 className="mx-auto size-6 animate-spin text-muted-foreground" />
        ) : methods?.microsoft ? (
          <MicrosoftLogin paste={methods.microsoft_paste} />
        ) : (
          <PasswordLogin />
        )}
      </div>
    </AuthLayout>
  )
}

function useSessionStart() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  return async (token: Token) => {
    localStorage.setItem("access_token", token.access_token)
    queryClient.clear()
    await navigate({ to: "/" })
  }
}

/**
 * Microsoft sign-in, completed by the backend. While the registered return
 * page is outside the application (Postman's), the user pastes its address.
 */
function MicrosoftLogin({ paste }: { paste: boolean }) {
  const { microsoft: ticket, microsoft_error } = Route.useSearch()
  const navigate = useNavigate()
  const startSession = useSessionStart()
  const [authUri, setAuthUri] = useState("")
  const [address, setAddress] = useState("")
  const [error, setError] = useState(microsoft_error ?? "")
  const redeemed = useRef(false)

  const redeem = useMutation({
    mutationFn: (value: string) =>
      LoginService.redeemMicrosoftTicket({ requestBody: { ticket: value } }),
    onSuccess: startSession,
    onError: handleError.bind(setError),
  })
  useEffect(() => {
    if (!ticket || redeemed.current) return
    redeemed.current = true
    // The ticket is single use: keep it out of the history.
    void navigate({ to: "/login", search: {}, replace: true })
    redeem.mutate(ticket)
  }, [ticket, navigate, redeem])

  const start = useMutation({
    mutationFn: async () => {
      // Opened within the click so that the browser does not block it.
      const popup = paste ? window.open("about:blank", "_blank") : null
      try {
        const { auth_uri } = await LoginService.startMicrosoftLogin()
        if (!paste) {
          window.location.assign(auth_uri)
          return
        }
        if (popup) {
          popup.opener = null
          popup.location.href = auth_uri
        }
        setAuthUri(auth_uri)
      } catch (failure) {
        popup?.close()
        throw failure
      }
    },
    onMutate: () => setError(""),
    onError: handleError.bind(setError),
  })
  const complete = useMutation({
    mutationFn: () =>
      LoginService.completeMicrosoftLogin({
        requestBody: { response_url: address.trim() },
      }),
    onMutate: () => setError(""),
    onSuccess: startSession,
    onError: handleError.bind(setError),
  })

  return (
    <div className="grid gap-5">
      <LoadingButton
        type="button"
        loading={start.isPending || redeem.isPending}
        className="h-12 w-full rounded-lg text-base font-semibold"
        onClick={() => start.mutate()}
      >
        Entrar con Microsoft
      </LoadingButton>
      {paste && authUri && (
        <form
          noValidate
          className="grid gap-3"
          onSubmit={(event) => {
            event.preventDefault()
            if (address.trim() && !complete.isPending) complete.mutate()
          }}
        >
          <p className="text-sm text-muted-foreground">
            Inicia sesión en la pestaña de Microsoft (
            <a
              href={authUri}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-primary underline underline-offset-4"
            >
              abrirla de nuevo
            </a>
            ). Al terminar, copia la dirección completa de la página a la que te
            lleva y pégala aquí.
          </p>
          <Input
            aria-label="Dirección de la página de retorno"
            placeholder="https://oauth.pstmn.io/v1/browser-callback?code=…"
            value={address}
            onChange={(event) => setAddress(event.target.value)}
            autoComplete="off"
            spellCheck={false}
            className="h-11 rounded-lg px-3.5"
          />
          <LoadingButton
            type="submit"
            variant="outline"
            loading={complete.isPending}
            disabled={!address.trim()}
            className="h-11 w-full rounded-lg"
          >
            Continuar
          </LoadingButton>
        </form>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}

function PasswordLogin() {
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
    <Form {...form}>
      <form
        noValidate
        onSubmit={form.handleSubmit(onSubmit)}
        className="flex flex-col gap-8"
      >
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
  )
}
