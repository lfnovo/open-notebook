export interface AuthState {
  isAuthenticated: boolean
  token: string | null
  isLoading: boolean
  error: string | null
}

export interface LoginCredentials {
  password: string
}