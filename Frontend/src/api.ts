export type Role = 'patient' | 'doctor' | 'admin'

export type Auth = {
  token: string
  username: string
  role: Role
  patient_id: number | null
}

export const apiUrl = import.meta.env.VITE_API_URL ?? '/api'

const STORAGE_KEY = 'careloop_auth'
export const LOGOUT_EVENT = 'careloop:logout'

export function getAuth(): Auth | null {
  const raw = localStorage.getItem(STORAGE_KEY)
  return raw ? (JSON.parse(raw) as Auth) : null
}

export function setAuth(auth: Auth | null): void {
  if (auth) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(auth))
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
}

/**
 * Attach the login token to every API call and log out on 401.
 * Wrapping window.fetch means components that call fetch directly
 * (e.g. CardDependencies) are covered without editing them.
 */
export function installAuthFetch(): void {
  const original = window.fetch.bind(window)
  window.fetch = async (input, init) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
    const auth = getAuth()
    if (auth && url.startsWith(apiUrl)) {
      const headers = new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined))
      headers.set('Authorization', `Bearer ${auth.token}`)
      init = { ...init, headers }
    }
    const response = await original(input, init)
    if (response.status === 401 && auth) {
      setAuth(null)
      window.dispatchEvent(new Event(LOGOUT_EVENT))
    }
    return response
  }
}

export async function responseError(response: Response): Promise<string> {
  const body = await response.json().catch(() => null) as { detail?: string } | null
  return body?.detail ?? `Request failed with status ${response.status}`
}
