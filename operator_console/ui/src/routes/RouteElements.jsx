import React from 'react'
import { useParams } from 'react-router-dom'
import RunDetail from '../pages/RunDetail.jsx'
import Snapshot from '../pages/Snapshot.jsx'
import EntityDetail from '../pages/EntityDetail.jsx'
import Steering from '../pages/Steering.jsx'
import DelegationPage from '../pages/DelegationPage.jsx'

export function RunDetailRoute() {
  const { runId } = useParams()
  return <RunDetail runId={runId} />
}

export function SnapshotRoute() {
  const { runId, seq } = useParams()
  return <Snapshot runId={runId} seq={seq} />
}

export function EntityDetailRoute() {
  const { entityId } = useParams()
  return <EntityDetail entityId={entityId} />
}

export function SteeringProfileRoute() {
  const { profileId } = useParams()
  return <Steering profileId={profileId} />
}

export function RunDelegationRoute() {
  const { runId } = useParams()
  return <DelegationPage runId={runId} />
}
