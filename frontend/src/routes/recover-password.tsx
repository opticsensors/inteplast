import { createFileRoute, redirect } from "@tanstack/react-router"

import { AuthLayout } from "@/components/Common/AuthLayout"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/recover-password")({
  component: RecoverPassword,
  beforeLoad: () => {
    if (isLoggedIn()) throw redirect({ to: "/" })
  },
  head: () => ({ meta: [{ title: "Recuperar contraseña - INTEPLAST" }] }),
})

function RecoverPassword() {
  return (
    <AuthLayout>
      <h1 className="text-center text-2xl font-bold">To be implemented</h1>
    </AuthLayout>
  )
}
