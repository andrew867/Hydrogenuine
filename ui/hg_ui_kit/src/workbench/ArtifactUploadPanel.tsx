import React from "react";
import { Badge } from "../components/Badge";

export type ArtifactUploadState = {
  status: "idle" | "hashing" | "uploading" | "uploaded" | "error";
  error?: string;
  last?: { filename: string; size_bytes: number; content_hash: string };
};

// Artifact panel with a REAL file input. Selecting a file hands the raw File to
// the container, which computes the expected sha256 (crypto.subtle) and uploads
// the bytes to the bounded local artifact store via the governed upload endpoint.
// The panel is prop-driven (no fetch of its own) so it renders in a browser and
// unit-tests without one. Boundary labels stay explicit: bytes go to a local
// store, the server computes the authoritative hash, no external effect occurs.
export function ArtifactUploadPanel({
  artifactIds,
  uploadState = { status: "idle" },
  onSelectFile,
  disabled,
}: {
  artifactIds: string[];
  uploadState?: ArtifactUploadState;
  onSelectFile?: (file: File) => void;
  disabled?: boolean;
}) {
  const busy = uploadState.status === "hashing" || uploadState.status === "uploading";
  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && onSelectFile) onSelectFile(file);
    e.target.value = ""; // allow re-selecting the same file
  };
  return (
    <div className="hg-artifact-upload-panel">
      <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
        <strong>Artifacts</strong>
        <Badge tone="default">local upload · server sha256 · no external effects</Badge>
      </div>
      <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
        {artifactIds.map((id) => (
          <li key={id}>
            <code>{id}</code>
          </li>
        ))}
      </ul>
      <label className="hg-artifact-upload-input" style={{ display: "block", marginTop: 6 }}>
        <span style={{ display: "block", fontSize: 12, opacity: 0.8 }}>
          Upload file bytes to the local run store
        </span>
        <input
          type="file"
          aria-label="Upload artifact file"
          disabled={disabled || busy}
          onChange={onChange}
        />
      </label>
      {uploadState.status === "hashing" ? (
        <div role="status" className="hg-upload-status">Hashing file…</div>
      ) : null}
      {uploadState.status === "uploading" ? (
        <div role="status" className="hg-upload-status">Uploading bytes to local store…</div>
      ) : null}
      {uploadState.status === "uploaded" && uploadState.last ? (
        <div role="status" className="hg-upload-status hg-upload-ok" data-testid="wb-upload-result">
          Stored <code>{uploadState.last.filename}</code> ·{" "}
          {uploadState.last.size_bytes} bytes ·{" "}
          <code>{uploadState.last.content_hash.slice(0, 23)}…</code>
        </div>
      ) : null}
      {uploadState.status === "error" ? (
        <div role="alert" className="hg-upload-status hg-upload-error">
          Upload failed: {uploadState.error ?? "unknown error"}
        </div>
      ) : null}
    </div>
  );
}
