export type AuthUser = {
  id: number
  email: string
  display_name: string
  avatar_url: string | null
  has_google_account: boolean
  onboarding_completed: boolean
}

export type AuthSession = {
  authenticated: boolean
  user: AuthUser | null
}
