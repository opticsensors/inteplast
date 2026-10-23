import { useQuery } from "@tanstack/react-query"

import { LoginService } from "@/client"

/** Password or Microsoft sign-in, and whether files come from SharePoint. */
export const useLoginMethods = () =>
  useQuery({
    queryKey: ["login-methods"],
    queryFn: () => LoginService.loginMethods(),
    staleTime: Number.POSITIVE_INFINITY,
  })
