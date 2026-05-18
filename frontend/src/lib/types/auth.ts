export interface AuthState {
  isAuthenticated: boolean
  token: string | null
  username: string | null
  role: 'admin' | 'user' | null
  displayName: string | null
  status: 'active' | 'disabled' | null
  requiresProfileCompletion: boolean
  isLoading: boolean
  error: string | null
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface AuthStatus {
  auth_enabled: boolean
  auth_method: 'legacy' | 'database' | 'disabled'
  has_users: boolean
  message: string
}

export interface LoginResponse {
  success: boolean
  token?: string
  username?: string
  message: string
}

export interface WeChatAuthorizeUrlResponse {
  enabled: boolean
  authorize_url?: string | null
  state?: string | null
  message?: string | null
}

export interface CurrentUserResponse {
  id?: string
  username: string
  email?: string | null
  display_name?: string | null
  avatar_url?: string | null
  login_provider?: string | null
  role?: 'admin' | 'user'
  status?: 'active' | 'disabled'
  locale?: string | null
  theme?: string | null
  created: string
  updated: string
  last_login_at?: string | null
}

export interface CompleteProfileResponse {
  success: boolean
  token: string
  user: CurrentUserResponse
  message: string
  bound_existing_user: boolean
}
