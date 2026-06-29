interface TelegramWebApp {
  ready: () => void
  expand: () => void
  close: () => void
  initDataUnsafe: {
    user?: { id: number; username?: string; first_name?: string; last_name?: string }
    start_param?: string
  }
  themeParams: Record<string, string>
  colorScheme: 'dark' | 'light'
  version: string
  platform: string
  HapticFeedback: {
    impactOccurred: (style: 'light' | 'medium' | 'heavy') => void
    notificationOccurred: (type: 'error' | 'success' | 'warning') => void
    selectionChanged: () => void
  }
  MainButton: {
    setText: (t: string) => void
    onClick: (cb: () => void) => void
    offClick: (cb: () => void) => void
    show: () => void
    hide: () => void
  }
  BackButton: {
    isVisible: boolean
    onClick: (cb: () => void) => void
    offClick: (cb: () => void) => void
    show: () => void
    hide: () => void
  }
  CloudStorage: {
    setItem: (key: string, value: string, cb?: (err: Error | null, result: boolean) => void) => void
    getItem: (key: string, cb: (err: Error | null, result: string | null) => void) => void
    removeItem: (key: string, cb?: (err: Error | null, result: boolean) => void) => void
    getKeys: (cb: (err: Error | null, result: string[]) => void) => void
  }
  showAlert: (msg: string, cb?: () => void) => void
  showConfirm: (msg: string, cb: (ok: boolean) => void) => void
}

interface Window {
  Telegram?: { WebApp: TelegramWebApp }
}
