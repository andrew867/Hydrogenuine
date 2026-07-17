import React, { useCallback, useEffect, useState } from 'react'
import { RecognitionActiveBadge } from 'hg_ui_kit'
import Layout from '../components/Layout.jsx'
import Breadcrumbs from '../components/Breadcrumbs.jsx'
import StateNotice from '../components/StateNotice.jsx'
import { api } from '../lib/api.js'

const DEFAULT_SUBJECT = 'demo-user'

export default function UserRecognition() {
  const [subjectId, setSubjectId] = useState(DEFAULT_SUBJECT)
  const [status, setStatus] = useState(null)
  const [templates, setTemplates] = useState([])
  const [analysis, setAnalysis] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    setErr(null)
    Promise.all([
      api.getUserRecognitionStatus(subjectId),
      api.getUserRecognitionTemplates(),
    ])
      .then(([st, tmpl]) => {
        setStatus(st)
        setTemplates(tmpl?.templates || [])
      })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [subjectId])

  useEffect(() => { load() }, [load])

  const runAnalyze = () => {
    setErr(null)
    api.analyzeUserRecognition({
      subject_id: subjectId,
      interaction: {
        messages: [
          { role: 'user', text: 'What if peace is a system — wit first, then the wound, then the song?' },
        ],
      },
      purpose: 'operator_panel',
    })
      .then(setAnalysis)
      .catch((e) => setErr(e.message))
  }

  return (
    <Layout title="User recognition">
      <Breadcrumbs items={[{ label: 'Home', href: '#/home' }, { label: 'User recognition' }]} />
      <h1>User recognition (telex)</h1>
      <p>Consent-gated cognitive kinship matching against fingerprint templates.</p>
      <div style={{ marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <label>
          Subject ID
          <input value={subjectId} onChange={(e) => setSubjectId(e.target.value)} style={{ marginLeft: 8 }} />
        </label>
        <RecognitionActiveBadge active={Boolean(status?.recognition_active)} />
        <button type="button" onClick={runAnalyze}>Analyze interaction</button>
        <button type="button" onClick={() => api.seedUserRecognitionDemo().then(load)}>Seed demo</button>
      </div>
      {loading && <StateNotice state="loading" message="Loading recognition status…" />}
      {err && <StateNotice state="error" message={err} />}
      {!loading && status && (
        <div data-testid="user-recognition-status">
          <p>Feature enabled: {String(status.feature_enabled)} · Consent: {status.consent_class}</p>
          <p>Templates loaded: {templates.length}</p>
        </div>
      )}
      {analysis?.top_match && (
        <div data-testid="user-recognition-result" style={{ marginTop: 16 }}>
          <strong>Top match:</strong> {analysis.top_match.label} ({analysis.top_match.similarity})
          {' · '}
          Kinship: {String(analysis.kinship_detected)}
        </div>
      )}
    </Layout>
  )
}
