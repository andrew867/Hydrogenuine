"use client";

import React, { useEffect, useState } from "react";
import { hgApi } from "@/lib/hgApi";
import { Icon } from "@/components/ui/Icon";
import { PageSkeleton } from "hg_ui_kit";

export function DocumentViewer({
  documentId,
  filename,
  mime: mimeProp,
  onClose,
  pageStart,
}: {
  documentId: string;
  filename: string;
  mime?: string;
  onClose: () => void;
  pageStart?: number;
}) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mime, setMime] = useState(mimeProp ?? "");

  useEffect(() => {
    if (!mimeProp && documentId) {
      hgApi.getDocument(documentId).then((doc) => {
        if (doc?.mime) setMime(doc.mime);
      });
    } else if (mimeProp) setMime(mimeProp);
  }, [documentId, mimeProp]);

  useEffect(() => {
    let url: string | null = null;
    (async () => {
      try {
        const blob = await hgApi.fetchFileBlob(documentId);
        url = URL.createObjectURL(blob);
        setBlobUrl(url);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load document");
      } finally {
        setLoading(false);
      }
    })();
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [documentId]);

  const isPdf = mime ? mime.toLowerCase().includes("pdf") : (filename || "").toLowerCase().endsWith(".pdf");
  const iframeSrc = blobUrl && isPdf && pageStart ? `${blobUrl}#page=${pageStart}` : blobUrl;

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-bg/95 backdrop-blur">
      <div className="flex items-center justify-between gap-2 px-4 py-2 border-b border-border/70">
        <span className="truncate text-sm font-medium">{filename}</span>
        <button
          type="button"
          className="p-2 rounded-xl hover:bg-bg/60 text-muted hover:text-text"
          onClick={onClose}
          aria-label="Close"
        >
          <Icon name="close" className="h-5 w-5" />
        </button>
      </div>
      <div className="flex-1 min-h-0 flex flex-col">
        {loading ? (
          <div className="flex items-center justify-center flex-1"><PageSkeleton label="Loading document" rows={6} /></div>
        ) : error ? (
          <div className="flex items-center justify-center flex-1 text-red-400">{error}</div>
        ) : blobUrl && isPdf ? (
          <iframe
            src={iframeSrc || blobUrl}
            title={filename}
            className="w-full flex-1 border-0"
          />
        ) : blobUrl ? (
          <div className="flex flex-col items-center justify-center flex-1 gap-4 p-4">
            <p className="text-muted text-sm">Preview not available for this file type.</p>
            <a
              href={blobUrl}
              download={filename}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-border/70 bg-card/60 hover:border-accent/60"
            >
              <Icon name="download" className="h-4 w-4" />
              Download
            </a>
          </div>
        ) : null}
      </div>
    </div>
  );
}
