import React, { useEffect, useState } from 'react'
import Layout from '../components/Layout.jsx'
import { api } from '../lib/api.js'
import { formatDateTime } from '../lib/timezone.js'
import StateNotice from '../components/StateNotice.jsx'
import { PageSkeleton } from '../components/PageStates.jsx'

const DEFAULT_LIMIT = 100

export default function Steering({ profileId = null }) {
  const [eventsData, setEventsData] = useState(null)
  const [configData, setConfigData] = useState(null)
  const [profilesData, setProfilesData] = useState(null)
  const [profileData, setProfileData] = useState(null)
  const [err, setErr] = useState(null)
  const [limit, setLimit] = useState(DEFAULT_LIMIT)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setErr(null)
    setLoading(true)
    try {
      const [events, config, profiles] = await Promise.all([
        api.getSteeringEvents(limit),
        api.getAuthorityConfig(),
        api.getSteeringProfiles(),
      ])
      setEventsData(events)
      setConfigData(config)
      setProfilesData(profiles)
    } catch (e) {
      setErr(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [limit])

  useEffect(() => {
    if (!profileId) {
      setProfileData(null)
      return
    }
    api.getSteeringProfile(profileId)
      .then(setProfileData)
      .catch(() => setProfileData(null))
  }, [profileId])

  if (err) {
    return (
      <Layout title="Steering">
        <StateNotice tone="danger" title="Could not load steering data" detail={err} action={<button type="button" onClick={load}>Retry</button>} />
      </Layout>
    )
  }

  const events = eventsData?.events ?? []
  const config = configData?.config ?? {}
  const profiles = profilesData?.profiles ?? []

  return (
    <Layout title="Steering">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <p style={{ margin: 0, color: 'var(--muted)' }}>
          {profiles.length} profiles, {events.length} steering events in the selected window.
        </p>
        <button type="button" onClick={load}>Refresh</button>
      </div>
      {loading && <StateNotice title="Loading steering data" detail="Fetching authority config, profiles, and recent steering events." />}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Authority config</h2>
        <pre style={{ fontSize: 12, overflow: 'auto', maxHeight: 200, background: 'var(--panel-2)', padding: 12 }}>
          {JSON.stringify(config, null, 2)}
        </pre>
      </section>
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>Steering profiles</h2>
        {profiles.length === 0 ? (
          <StateNotice title="No steering profiles" detail="Factory automation profiles have not been published into the operator control plane yet." />
        ) : (
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {profiles.map((id) => (
              <li key={id} style={{ marginBottom: 4 }}>
                <a href={`#/steering/profiles/${id}`}>{id}</a>
              </li>
            ))}
          </ul>
        )}
      </section>
      {profileId && profileData && (
        <section style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 18, marginBottom: 8 }}>Profile: {profileId}</h2>
          <pre style={{ fontSize: 12, overflow: 'auto', maxHeight: 300, background: 'var(--panel-2)', padding: 12 }}>
            {JSON.stringify(profileData.profile, null, 2)}
          </pre>
        </section>
      )}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 8 }}>
          Steering events
          <span style={{ marginLeft: 8, fontWeight: 'normal', fontSize: 14 }}>
            <label>
              Limit:{' '}
              <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={200}>200</option>
                <option value={500}>500</option>
              </select>
            </label>
          </span>
        </h2>
        {!eventsData ? (
          <PageSkeleton label="Loading steering events" />
        ) : events.length === 0 ? (
          <StateNotice title="No steering events" detail="No steering overrides or policy adjustments were recorded in the selected window." />
        ) : (
          <table width="100%" cellPadding="8" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                <th>Timestamp</th>
                <th>Event</th>
                <th>Agent</th>
                <th>Run</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {events.map((ev, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td>{formatDateTime(ev.timestamp)}</td>
                  <td>{ev.event ?? '—'}</td>
                  <td>{ev.agent_id ?? '—'}</td>
                  <td>{ev.run_id ?? '—'}</td>
                  <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {ev.details != null ? (typeof ev.details === 'string' ? ev.details : JSON.stringify(ev.details)).slice(0, 80) + '…' : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </Layout>
  )
}


