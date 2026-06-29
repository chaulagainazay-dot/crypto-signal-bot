import useSWR from 'swr'
import { fetchGlobal, fetchTopCoins, fetchTrending, fetchCoinDetail, fetchFearGreed } from '../api/coingecko'

export function useGlobalMarket() {
  return useSWR('global', fetchGlobal, { refreshInterval: 60000, revalidateOnFocus: false })
}

export function useTopCoins(limit = 100) {
  const { data, error, isLoading, mutate } = useSWR(
    ['coins', limit],
    () => fetchTopCoins(limit),
    { refreshInterval: 15000, revalidateOnFocus: true }
  )
  return { data: data || [], error, isLoading, refetch: mutate }
}

export function useTrendingCoins() {
  const { data, error, isLoading } = useSWR('trending', fetchTrending, {
    refreshInterval: 300000, revalidateOnFocus: false,
  })
  return { data: data || [], error, isLoading }
}

export function useCoinDetail(id: string | null) {
  return useSWR(id ? ['coin', id] : null, () => id ? fetchCoinDetail(id) : null, {
    revalidateOnFocus: false,
  })
}

export function useFearGreed() {
  return useSWR('feargreed', fetchFearGreed, { refreshInterval: 300000, revalidateOnFocus: false })
}
