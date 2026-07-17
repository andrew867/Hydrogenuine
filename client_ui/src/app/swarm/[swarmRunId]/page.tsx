import { SwarmOrchestratorView } from "@/components/swarm/SwarmOrchestratorView";

export default async function SwarmPage({ params }: { params: Promise<{ swarmRunId: string }> }) {
  const { swarmRunId } = await params;
  return <SwarmOrchestratorView swarmRunId={swarmRunId} />;
}
