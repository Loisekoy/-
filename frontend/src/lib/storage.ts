const STORAGE_KEY = 'fitness-tracker:user:v1'
const ADMIN_TOKEN_KEY = 'fitness-tracker:admin-token:v1'

interface StoredProfilePointer {
  version: 1
  userId: string
}

export function saveUserId(userId: string): void {
  const value: StoredProfilePointer = { version: 1, userId }
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
  } catch {
    // Private browsing and strict privacy settings may block storage.
  }
}

export function getUserId(): string | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const value = JSON.parse(raw) as Partial<StoredProfilePointer>
    return value.version === 1 && typeof value.userId === 'string' ? value.userId : null
  } catch {
    return null
  }
}

export function clearUserId(): void {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // No action is required when local storage is unavailable.
  }
}

export function saveAdminToken(token: string): void {
  try {
    localStorage.setItem(ADMIN_TOKEN_KEY, token)
  } catch {
    // Private browsing and strict privacy settings may block storage.
  }
}

export function getAdminToken(): string | null {
  try {
    return localStorage.getItem(ADMIN_TOKEN_KEY)
  } catch {
    return null
  }
}

export function clearAdminToken(): void {
  try {
    localStorage.removeItem(ADMIN_TOKEN_KEY)
  } catch {
    // No action is required when local storage is unavailable.
  }
}
