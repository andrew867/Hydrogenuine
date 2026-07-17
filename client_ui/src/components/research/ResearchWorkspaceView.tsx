"use client";

import React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import type { Citation, KnowledgeWorkspaceDocument, KnowledgeWorkspaceRun } from "@/types/hg";
import { Badge } from "@/components/ui/Badge";
import { Icon } from "@/components/ui/Icon";
import { DocumentViewer } from "@/components/documents/DocumentViewer";
import { SourceEvidenceCards } from "@/components/chat/SourceEvidenceCards";
import { HardNavLink } from "@/components/navigation/HardNavLink";

function PlanSummaryCard({
  title,
  loading,
  summary,
  empty,
}: {
  title: string;
  loading: boolean;
  summary: null | {
    template?: string | null;
    confidence?: number | null;
    node_count?: number;
    inputs?: Record<string, unknown>;
  };
  empty: string;
}) {
  return (
    <div className="rounded-[24px] border border-border/70 bg-card/40 p-4">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="text-sm font-semibold">{title}</div>
        {loading ? <Badge tone="warning">Planning…</Badge> : null}
      </div>
      {!summary ? (
        <div className="text-sm text-muted">{empty}</div>
      ) : (
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {summary.template ? <Badge tone="neutral">{summary.template}</Badge> : null}
            {summary.node_count != null ? <Badge tone="neutral">{summary.node_count} nodes</Badge> : null}
            {summary.confidence != null ? <Badge tone="ok">{Math.round(summary.confidence * 100)}% confidence</Badge> : null}
          </div>
          {summary.inputs ? (
            <pre className="overflow-x-auto rounded-2xl border border-border/70 bg-bg/50 p-3 text-xs text-muted">
              {JSON.stringify(summary.inputs, null, 2)}
            </pre>
          ) : null}
        </div>
      )}
    </div>
  );
}

function RunCard({ run, onCitationClick }: { run: KnowledgeWorkspaceRun; onCitationClick: (citation: Citation) => void }) {
  return (
    <div className="rounded-[24px] border border-border/70 bg-card/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold">{run.title}</div>
          <div className="mt-1 text-xs text-muted">{new Date(run.created_at).toLocaleString()}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone={run.kind === "research_summary" ? "accent" : "warning"}>
            {run.kind === "research_summary" ? "Research" : "Document review"}
          </Badge>
          {run.plan_template ? <Badge tone="neutral">{run.plan_template}</Badge> : null}
          {run.swarm_run_id ? (
            <HardNavLink
              href={`/swarm/${encodeURIComponent(run.swarm_run_id)}`}
              className="inline-flex rounded-full border border-border/70 px-2 py-0.5 text-[11px] uppercase tracking-wide text-muted hover:bg-card/60"
            >
              Open swarm
            </HardNavLink>
          ) : null}
        </div>
      </div>
      {run.query ? <div className="mt-3 text-sm text-text">Query: {run.query}</div> : null}
      {run.segment_labels?.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {run.segment_labels.map((label) => (
            <Badge key={label} tone="neutral">
              {label}
            </Badge>
          ))}
        </div>
      ) : null}
      {run.assistant_excerpt ? <div className="mt-3 text-sm text-muted">{run.assistant_excerpt}</div> : null}
      {run.sources?.length ? (
        <div className="mt-3">
          <SourceEvidenceCards sources={run.sources} />
        </div>
      ) : null}
      {run.document_id ? (
        <div className="mt-3">
          <button
            type="button"
            onClick={() => {
              if (!run.document_id) return;
              onCitationClick({ document_id: run.document_id, filename: run.title, page_start: 1 });
            }}
            className="rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm hover:bg-card/60"
          >
            Open document
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function ResearchWorkspaceView({ chatId }: { chatId: string }) {
  const qc = useQueryClient();
  const [query, setQuery] = React.useState("");
  const [researchPrompt, setResearchPrompt] = React.useState("Search online, compare the strongest sources, and give me the key points that matter.");
  const [documentPrompt, setDocumentPrompt] = React.useState("Read the attached document in parallel, summarize each segment, then reduce it into one clear answer.");
  const [retrievalResults, setRetrievalResults] = React.useState<Array<{ chunk_id: string; text: string; citation?: Citation; score?: number }>>([]);
  const [retrieving, setRetrieving] = React.useState(false);
  const [researchPreview, setResearchPreview] = React.useState<null | { template?: string | null; confidence?: number | null; node_count?: number; inputs?: Record<string, unknown> }>(null);
  const [researchPlanning, setResearchPlanning] = React.useState(false);
  const [documentPreview, setDocumentPreview] = React.useState<null | { template?: string | null; confidence?: number | null; node_count?: number; inputs?: Record<string, unknown> }>(null);
  const [documentPlanning, setDocumentPlanning] = React.useState(false);
  const [viewCitation, setViewCitation] = React.useState<Citation | null>(null);

  const { data: workspace, isLoading } = useQuery({
    queryKey: ["knowledge-workspace", chatId],
    queryFn: () => hgApi.getKnowledgeWorkspace(chatId),
    refetchInterval: 3000,
  });

  const handleRetrieve = async () => {
    const normalized = query.trim();
    if (!normalized) return;
    setRetrieving(true);
    try {
      const result = await hgApi.retrieveDocuments({ query: normalized, chat_id: chatId, top_k: 6 });
      setRetrievalResults(result.chunks);
    } finally {
      setRetrieving(false);
    }
  };

  const handleResearchPreview = async () => {
    const normalized = researchPrompt.trim();
    if (!normalized) return;
    setResearchPlanning(true);
    try {
      const result = await hgApi.previewResearchPlan(chatId, normalized);
      setResearchPreview(result.plan ?? null);
    } finally {
      setResearchPlanning(false);
    }
  };

  const handleDocumentPreview = async (documentId?: string) => {
    const normalized = documentPrompt.trim();
    if (!normalized) return;
    setDocumentPlanning(true);
    try {
      const result = await hgApi.previewDocumentPlan(chatId, {
        content: normalized,
        document_id: documentId,
      });
      setDocumentPreview(result.plan ?? null);
      await qc.invalidateQueries({ queryKey: ["knowledge-workspace", chatId] });
    } finally {
      setDocumentPlanning(false);
    }
  };

  const documents = workspace?.documents ?? [];
  const runs = workspace?.runs ?? [];

  return (
    <div className="min-h-full bg-[radial-gradient(circle_at_top,#183342,transparent_48%),linear-gradient(180deg,rgba(8,17,24,0.98),rgba(7,10,14,1))]">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-8">
        <section className="rounded-[32px] border border-border/70 bg-card/40 p-6 shadow-soft backdrop-blur">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <div className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-accent">Research Workspace</div>
              <h1 className="text-3xl font-semibold tracking-tight text-text sm:text-4xl">
                {workspace?.chat.title || "Knowledge work"}
              </h1>
              <p className="mt-3 text-sm text-muted">
                Upload source material, preview the plan, run retrieval-backed work, and inspect the resulting summaries without digging through raw tool messages.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <HardNavLink
                href={`/chat/${encodeURIComponent(chatId)}`}
                className="inline-flex items-center gap-2 rounded-2xl border border-border/70 bg-bg/40 px-4 py-3 text-sm hover:bg-card/60"
              >
                Back to chat
              </HardNavLink>
              <button
                type="button"
                onClick={() => void qc.invalidateQueries({ queryKey: ["knowledge-workspace", chatId] })}
                className="inline-flex items-center gap-2 rounded-2xl border border-border/70 bg-bg/40 px-4 py-3 text-sm hover:bg-card/60"
              >
                <Icon name="refresh" className="h-4 w-4" />
                Refresh
              </button>
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-6">
            <div className="rounded-[28px] border border-border/70 bg-card/40 p-5">
              <div className="mb-3 flex items-center justify-between gap-2">
                <div>
                  <div className="text-sm font-semibold">Attached documents</div>
                  <div className="text-xs text-muted">Each document shows parse state and cached segment groups.</div>
                </div>
                <Badge tone="neutral">{documents.length}</Badge>
              </div>
              {isLoading ? <div className="text-sm text-muted">Loading workspace…</div> : null}
              {!isLoading && !documents.length ? <div className="text-sm text-muted">No attached documents yet. Add a PDF or DOCX from the chat details rail.</div> : null}
              {documents.length ? (
                <div className="grid gap-3">
                  {documents.map((doc: KnowledgeWorkspaceDocument) => (
                    <div key={doc.document_id} className="rounded-[22px] border border-border/70 bg-bg/40 p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="font-medium">{doc.filename}</div>
                          <div className="mt-1 text-xs text-muted">{doc.mime} · {(doc.size_bytes / 1024).toFixed(1)} KB</div>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Badge tone={doc.parse_status === "parsed" ? "ok" : doc.parse_status === "failed" ? "danger" : "warning"}>
                            {doc.parse_status}
                          </Badge>
                          <Badge tone="neutral">{doc.segments?.length ?? 0} segments</Badge>
                        </div>
                      </div>
                      {doc.segments?.length ? (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {doc.segments.map((segment) => (
                            <button
                              key={segment.segment_id}
                              type="button"
                              onClick={() =>
                                setViewCitation({
                                  document_id: doc.document_id,
                                  filename: doc.filename,
                                  page_start: segment.page_start,
                                  page_end: segment.page_end,
                                })
                              }
                              className="rounded-full border border-border/70 px-3 py-1 text-xs text-muted hover:bg-card/60"
                            >
                              {segment.label}
                            </button>
                          ))}
                        </div>
                      ) : null}
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => setViewCitation({ document_id: doc.document_id, filename: doc.filename, page_start: 1 })}
                          className="rounded-xl border border-border/70 bg-bg/40 px-3 py-2 text-sm hover:bg-card/60"
                        >
                          Open document
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleDocumentPreview(doc.document_id)}
                          className="rounded-xl border border-accent/30 bg-accent/10 px-3 py-2 text-sm hover:bg-accent/20"
                        >
                          Preview document plan
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-[28px] border border-border/70 bg-card/40 p-5">
                <div className="mb-3 text-sm font-semibold">Research plan preview</div>
                <textarea
                  value={researchPrompt}
                  onChange={(event) => setResearchPrompt(event.target.value)}
                  className="min-h-[120px] w-full rounded-2xl border border-border/70 bg-bg/40 px-4 py-3 text-sm outline-none focus:border-accent/60"
                />
                <div className="mt-3 flex justify-end">
                  <button
                    type="button"
                    onClick={() => void handleResearchPreview()}
                    className="rounded-xl border border-accent/30 bg-accent/10 px-4 py-2 text-sm hover:bg-accent/20"
                  >
                    Preview plan
                  </button>
                </div>
                <div className="mt-4">
                  <PlanSummaryCard
                    title="Planner output"
                    loading={researchPlanning}
                    summary={researchPreview}
                    empty="Preview the research plan to see the selected template and DAG inputs."
                  />
                </div>
              </div>

              <div className="rounded-[28px] border border-border/70 bg-card/40 p-5">
                <div className="mb-3 text-sm font-semibold">Document review plan preview</div>
                <textarea
                  value={documentPrompt}
                  onChange={(event) => setDocumentPrompt(event.target.value)}
                  className="min-h-[120px] w-full rounded-2xl border border-border/70 bg-bg/40 px-4 py-3 text-sm outline-none focus:border-accent/60"
                />
                <div className="mt-3 flex justify-end">
                  <button
                    type="button"
                    onClick={() => void handleDocumentPreview(documents[0]?.document_id)}
                    className="rounded-xl border border-accent/30 bg-accent/10 px-4 py-2 text-sm hover:bg-accent/20"
                  >
                    Preview fan-out
                  </button>
                </div>
                <div className="mt-4">
                  <PlanSummaryCard
                    title="Planner output"
                    loading={documentPlanning}
                    summary={documentPreview}
                    empty="Preview the document decomposition plan to see segment groups and fan-out inputs."
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-[28px] border border-border/70 bg-card/40 p-5">
              <div className="mb-3 text-sm font-semibold">Retrieval sandbox</div>
              <div className="flex gap-2">
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") void handleRetrieve();
                  }}
                  placeholder="Ask for the exact clause, page, or topic you want to ground."
                  className="flex-1 rounded-2xl border border-border/70 bg-bg/40 px-4 py-3 text-sm outline-none focus:border-accent/60"
                />
                <button
                  type="button"
                  onClick={() => void handleRetrieve()}
                  className="rounded-2xl border border-border/70 bg-bg/40 px-4 py-3 text-sm hover:bg-card/60"
                >
                  {retrieving ? "Searching…" : "Retrieve"}
                </button>
              </div>
              <div className="mt-4 space-y-3">
                {retrievalResults.map((chunk) => (
                  <div key={chunk.chunk_id} className="rounded-[22px] border border-border/70 bg-bg/40 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-xs text-muted">{chunk.citation?.filename || chunk.citation?.document_id || chunk.chunk_id}</div>
                      {chunk.score != null ? <Badge tone="neutral">score {(chunk.score ?? 0).toFixed(3)}</Badge> : null}
                    </div>
                    <div className="mt-2 text-sm text-muted">{chunk.text}</div>
                    {chunk.citation?.document_id ? (
                      <div className="mt-3">
                        <button
                          type="button"
                          onClick={() => setViewCitation(chunk.citation || null)}
                          className="rounded-xl border border-border/70 bg-card/40 px-3 py-2 text-sm hover:bg-card/60"
                        >
                          Open citation
                        </button>
                      </div>
                    ) : null}
                  </div>
                ))}
                {!retrievalResults.length ? <div className="text-sm text-muted">No retrieval results yet.</div> : null}
              </div>
            </div>

            <div className="rounded-[28px] border border-border/70 bg-card/40 p-5">
              <div className="mb-3 flex items-center justify-between gap-2">
                <div>
                  <div className="text-sm font-semibold">Recent runs</div>
                  <div className="text-xs text-muted">The structured view over planner-backed research and document decomposition in this chat.</div>
                </div>
                <Badge tone="neutral">{runs.length}</Badge>
              </div>
              <div className="space-y-3">
                {runs.map((run) => (
                  <RunCard key={run.message_id} run={run} onCitationClick={setViewCitation} />
                ))}
                {!runs.length ? <div className="text-sm text-muted">No planner-backed runs have been recorded in this chat yet.</div> : null}
              </div>
            </div>
          </div>
        </section>
      </div>

      {viewCitation?.document_id ? (
        <DocumentViewer
          documentId={viewCitation.document_id}
          filename={viewCitation.filename ?? viewCitation.document_id}
          mime={undefined}
          onClose={() => setViewCitation(null)}
          pageStart={viewCitation.page_start}
        />
      ) : null}
    </div>
  );
}
