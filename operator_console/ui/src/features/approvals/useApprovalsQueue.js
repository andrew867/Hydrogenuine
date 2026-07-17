import { useCallback, useEffect, useState } from 'react'
import { api } from '../../lib/api.js'

/** Shared hook for operator runtime approvals queue (U6 decomposition seed). */
export function useApprovalsQueue(params = {}) {
  const [data, setData] = useState({ items: [], total: 0, evidence_timeline: null })
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setErr(null)
    api
      .getApprovalsQueue(params)
      .then((r) => setData({
        items: Array.isArray(r.items) ? r.items : [],
        total: r.total ?? 0,
        evidence_timeline: r.evidence_timeline ?? null,
      }))
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [JSON.stringify(params)])

  useEffect(() => {
    load()
  }, [load])

  return { ...data, err, loading, reload: load }
}
