import { createFileRoute, Link, redirect } from "@tanstack/react-router"

import { AuthLayout } from "@/components/Common/AuthLayout"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/signup")({
  component: SignUp,
  beforeLoad: () => {
    if (isLoggedIn()) throw redirect({ to: "/" })
  },
  head: () => ({ meta: [{ title: "Solicitar acceso - INTEPLAST" }] }),
})

function SignUp() {
  return (
    <AuthLayout>
      <div className="space-y-4 text-center">
        <h1 className="text-2xl font-bold">Solicitar acceso</h1>
        <p>Contacta con el administrador para solicitar una cuenta.</p>
        <Link to="/login" className="underline">
          Volver al inicio de sesion
        </Link>
      </div>
    </AuthLayout>
  )
}
