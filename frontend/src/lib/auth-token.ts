// Reads the auth token persisted by the zustand auth store
// (localStorage key `auth-storage`, written by `src/lib/stores/auth-store.ts`).
// Single source of truth for the token-parsing ritual — use this instead of
// re-reading localStorage directly.
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') {
    return null
  }

  const raw = window.localStorage.getItem('auth-storage')
  if (!raw) {
    return null
  }

  try {
    const { state } = JSON.parse(raw)
    return state?.token ?? null
  } catch (error) {
    console.error('Error parsing auth storage:', error)
    return null
  }
}
