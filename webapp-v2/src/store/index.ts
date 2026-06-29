import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { Coin, Holding, PriceAlert, UserState, Signal } from '../types'

interface AppState {
  user: UserState
  setUser: (u: Partial<UserState>) => void

  coins: Coin[]
  setCoins: (coins: Coin[]) => void
  updateCoinPrice: (symbol: string, price: number) => void

  holdings: Holding[]
  addHolding: (h: Holding) => void
  removeHolding: (id: string) => void

  alerts: PriceAlert[]
  addAlert: (a: PriceAlert) => void
  removeAlert: (id: string) => void
  triggerAlert: (id: string) => void

  signals: Signal[]
  setSignals: (s: Signal[]) => void

  activeTab: string
  setActiveTab: (tab: string) => void

  researchCoinId: string | null
  setResearchCoinId: (id: string | null) => void
}

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      user: { telegramId: null, username: null, theme: 'dark', currency: 'USD' },
      setUser: (u) => set((s) => ({ user: { ...s.user, ...u } })),

      coins: [],
      setCoins: (coins) => set({ coins }),
      updateCoinPrice: (symbol, price) => set((s) => ({
        coins: s.coins.map(c => c.symbol.toUpperCase() === symbol.toUpperCase() ? { ...c, current_price: price } : c),
      })),

      holdings: [],
      addHolding: (h) => set((s) => ({ holdings: [...s.holdings, h] })),
      removeHolding: (id) => set((s) => ({ holdings: s.holdings.filter(h => h.id !== id) })),

      alerts: [],
      addAlert: (a) => set((s) => ({ alerts: [...s.alerts, a] })),
      removeAlert: (id) => set((s) => ({ alerts: s.alerts.filter(a => a.id !== id) })),
      triggerAlert: (id) => set((s) => ({
        alerts: s.alerts.map(a => a.id === id ? { ...a, triggered: Date.now(), active: false } : a),
      })),

      signals: [],
      setSignals: (signals) => set({ signals }),

      activeTab: 'guide',
      setActiveTab: (tab) => set({ activeTab: tab }),

      researchCoinId: null,
      setResearchCoinId: (id) => set({ researchCoinId: id }),
    }),
    {
      name: 'hcg-v2-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ user: s.user, holdings: s.holdings, alerts: s.alerts }),
    }
  )
)
