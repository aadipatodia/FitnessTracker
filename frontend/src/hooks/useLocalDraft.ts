import { useEffect, useRef } from 'react'

const SAVE_DEBOUNCE_MS = 400

export function loadDraft<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}

export function clearDraft(key: string) {
  localStorage.removeItem(key)
}

/** Debounce-saves `value` to localStorage under `key` while `enabled` is true. */
export function useLocalDraft<T>(key: string, value: T, enabled: boolean) {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  useEffect(() => {
    if (!enabled) return
    timeoutRef.current = setTimeout(() => {
      try {
        localStorage.setItem(key, JSON.stringify(value))
      } catch {
        // localStorage unavailable or quota exceeded — draft persistence is best-effort
      }
    }, SAVE_DEBOUNCE_MS)
    return () => clearTimeout(timeoutRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, enabled, JSON.stringify(value)])
}
