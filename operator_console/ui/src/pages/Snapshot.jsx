import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import JsonBlock from '../components/JsonBlock.jsx'
import { api } from '../lib/api.js'
import { AsyncPageBody } from '../components/PageStates.jsx'

export default function Snapshot({ runId, seq }) {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [forking, setForking] = useState(false)

  useEffect(() => {
    api.getSnapshot(runId, Number(seq)).then(setData).catch(e => setErr(e.message))
  }, [runId, seq])

  const onFork = async () => {
    setForking(true)
    setErr(null)
    try {
      const res = await api.forkFromSnapshot(runId, Number(seq))
      if (res.ok && res.run_id) {
        window.location.hash = `#/runs/${res.run_id}`
      } else {
        setErr(res.error?.message || 'Fork request failed')
      }
    } catch (e) {
      setErr(e.message)
    } finally {
      setForking(false)
    }
  }

  return (
    <Layout title={`Snapshot ${runId} seq ${seq}`}>
      <AsyncPageBody loading={!data && !err} error={err} loadingLabel="Loading snapshot">
      {data && (
        <>
          <JsonBlock value={data.state || {}} />
          <div style={{ marginTop: 12 }}>
            <button onClick={onFork} disabled={forking} style={{ padding:'8px 12px', borderRadius: 8 }}>
              {forking ? 'Forking...' : 'Fork from this snapshot'}
            </button>
            <span style={{ marginLeft: 8, color:'var(--muted)' }}>Creates a new run from this state.</span>
          </div>
        </>
      )}
      <p style={{ marginTop: 16 }}><a href={`#/runs/${runId}`}>Back to run</a></p>
      </AsyncPageBody>
    </Layout>
  )
}


