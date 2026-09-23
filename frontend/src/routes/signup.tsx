import { createFileRoute, redirect } from "@tanstack/react-router"

import { AuthLayout } from "@/components/Common/AuthLayout"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/signup")({
  component: SignUp,
  beforeLoad: () => {
    if (isLoggedIn()) throw redirect({ to: "/" })
  },
  head: () => ({ meta: [{ title: "Crear una cuenta - INTEPLAST" }] }),
})

function SignUp() {
  return (
    <AuthLayout>
      <h1 className="text-center text-2xl font-bold">To be implemented</h1>
    </AuthLayout>
  )
}
