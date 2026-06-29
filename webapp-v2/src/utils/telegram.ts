import '../telegram.d.ts'

export const tg = typeof window !== 'undefined' ? window.Telegram?.WebApp : undefined

export function initTelegram() {
  if (!tg) return
  tg.ready()
  tg.expand()
}

export function getTelegramUser() {
  return tg?.initDataUnsafe?.user ?? null
}

export function hapticImpact(style: 'light' | 'medium' | 'heavy' = 'light') {
  tg?.HapticFeedback?.impactOccurred(style)
}

export function hapticNotify(type: 'error' | 'success' | 'warning') {
  tg?.HapticFeedback?.notificationOccurred(type)
}

export function cloudSet(key: string, value: string): Promise<boolean> {
  return new Promise((resolve) => {
    if (!tg?.CloudStorage) { localStorage.setItem(key, value); resolve(true); return }
    tg.CloudStorage.setItem(key, value, (err, result) => resolve(!err && result))
  })
}

export function cloudGet(key: string): Promise<string | null> {
  return new Promise((resolve) => {
    if (!tg?.CloudStorage) { resolve(localStorage.getItem(key)); return }
    tg.CloudStorage.getItem(key, (err, result) => resolve(err ? null : result))
  })
}

export function cloudRemove(key: string): Promise<boolean> {
  return new Promise((resolve) => {
    if (!tg?.CloudStorage) { localStorage.removeItem(key); resolve(true); return }
    tg.CloudStorage.removeItem(key, (err, result) => resolve(!err && result))
  })
}
