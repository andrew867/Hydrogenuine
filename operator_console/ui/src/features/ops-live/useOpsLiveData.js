import { useCallback, useEffect, useState } from 'react'
import { api } from '../../lib/api.js'

export function useOpsLiveData() {
  const [entities, setEntities] = useState([])
  const [overview, setOverview] = useState(null)
  const [incidents, setIncidents] = useState([])
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setErr(null)
    Promise.allSettled([
      api.listEntities(),
      api.getOperatorStatusOverview(),
      api.getIncidentQueue(),
    ])
      .then(([entitiesRes, overviewRes, incidentsRes]) => {
        if (entitiesRes.status === 'fulfilled') {
          const payload = entitiesRes.value
          setEntities(Array.isArray(payload?.entities) ? payload.entities : [])
        }
        if (overviewRes.status === 'fulfilled') {
          setOverview(overviewRes.value)
        }
        if (incidentsRes.status === 'fulfilled') {
          const payload = incidentsRes.value
          setIncidents(Array.isArray(payload?.items) ? payload.items : [])
        }
        const failures = []
        if (entitiesRes.status === 'rejected') failures.push('entities')
        if (overviewRes.status === 'rejected') failures.push('status-overview')
        if (incidentsRes.status === 'rejected') failures.push('incidents')
        if (failures.length) setErr(`Failed to load: ${failures.join(', ')}`)
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
    const timer = window.setInterval(load, 30_000)
    return () => window.clearInterval(timer)
  }, [load])

  return { entities, overview, incidents, err, loading, reload: load }
}
