import { useCallback, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEventChannel } from 'hg_ui_kit'
import { api } from '../../lib/api.js'

export function useRunsData() {
  const qc = useQueryClient()
  const [channelHealthy, setChannelHealthy] = useState(false)
  const [staleCancelling, setStaleCancelling] = useState(false)
  const [staleResult, setStaleResult] = useState(null)

  const { data: runs = [], isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['runs'],
    queryFn: async () => {
      const payload = await api.listRuns(500)
      return payload.runs || []
    },
    refetchInterval: channelHealthy ? false : 30_000,
  })

  useEventChannel({
    streamUrl: api.runsStreamUrl(),
    enabled: true,
    onEvent: (event) => {
      if (event.type !== 'runs.delta') return
      const payload = event.data
      const nextRuns = Array.isArray(payload?.runs)
        ? payload.runs
        : Array.isArray(payload)
          ? payload
          : null
      if (nextRuns) {
        qc.setQueryData(['runs'], nextRuns)
        setChannelHealthy(true)
      }
    },
  })

  const load = useCallback(() => {
    void refetch()
  }, [refetch])

  const cancelStale = () => {
    setStaleResult(null)
    setStaleCancelling(true)
    api.cancelStaleRuns(0)
      .then((res) => {
        setStaleResult(res)
        void refetch()
      })
      .catch((e) => setStaleResult({ ok: false, error: e.message }))
      .finally(() => setStaleCancelling(false))
  }

  const err = error instanceof Error ? error.message : error ? String(error) : null

  return {
    runs,
    isLoading,
    isFetching,
    err,
    load,
    cancelStale,
    staleCancelling,
    staleResult,
    channelHealthy,
  }
}
