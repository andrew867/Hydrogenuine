"use client";

import React, { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import type { Document as DocType } from "@/types/hg";
import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/cn";
import { DocumentViewer } from "./DocumentViewer";
import { PageSkeleton } from "hg_ui_kit";

export function DocumentSidebar({ chatId }: { chatId: string }) {
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [viewDoc, setViewDoc] = useState<DocType | null>(null);

  useEffect(() => {
    setStatusMessage(null);
    setErrorMessage(null);
    setViewDoc(null);
  }, [chatId]);

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ["documents", chatId],
    queryFn: () => hgApi.listDocuments(chatId),
  });

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setErrorMessage(null);
    setStatusMessage(`Uploading ${file.name}…`);
    try {
      const res = await hgApi.uploadFile(file);
      const existing = await hgApi.getChatAttachments(chatId);
      await hgApi.setChatAttachments(chatId, [...existing, res.document_id]);
      setStatusMessage(`Parsing ${res.filename}…`);
      await hgApi.parseDocument(res.document_id);
      await qc.invalidateQueries({ queryKey: ["documents", chatId] });
      setStatusMessage(`${res.filename} is attached and parsed.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Upload failed");
      setStatusMessage(null);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleParse = async (doc: DocType) => {
    try {
      await hgApi.parseDocument(doc.document_id);
      await qc.invalidateQueries({ queryKey: ["documents", chatId] });
    } catch (_) {
      // Error surfaced by API
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-semibold">Documents</span>
        <div className="flex items-center gap-1">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.doc"
            className="hidden"
            onChange={handleUpload}
            disabled={uploading}
          />
          <button
            type="button"
            className="p-2 rounded-xl border border-border/70 bg-card/60 hover:border-accent/60 disabled:opacity-50"
            title="Upload document"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            <Icon name="plus" className="h-4 w-4" />
          </button>
        </div>
      </div>
      {statusMessage ? <div className="text-xs text-accent">{statusMessage}</div> : null}
      {errorMessage ? <div className="text-xs text-red-400">{errorMessage}</div> : null}
      {isLoading ? (
        <PageSkeleton label="Loading documents" rows={4} />
      ) : documents.length === 0 ? (
        <div className="text-xs text-muted">No documents. Upload a PDF or DOCX.</div>
      ) : (
        <ul className="space-y-2">
          {documents.map((doc) => (
            <li
              key={doc.document_id}
              className={cn(
                "rounded-xl border border-border/70 bg-card/50 p-2 text-sm",
                "flex flex-col gap-1"
              )}
            >
              <div className="flex items-center gap-2 min-w-0">
                <Icon name="file" className="h-4 w-4 shrink-0 text-muted" />
                <span className="truncate font-medium" title={doc.filename}>
                  {doc.filename}
                </span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span
                  className={cn(
                    "text-xs px-1.5 py-0.5 rounded",
                    doc.parse_status === "parsed" && "bg-green-500/20 text-green-400",
                    doc.parse_status === "pending" && "bg-amber-500/20 text-amber-400",
                    doc.parse_status === "failed" && "bg-red-500/20 text-red-400"
                  )}
                >
                  {doc.parse_status}
                </span>
                <div className="flex items-center gap-0.5">
                  <button
                    type="button"
                    className="p-1 rounded-lg hover:bg-bg/60 text-muted hover:text-text"
                    title="View"
                    onClick={() => setViewDoc(doc)}
                  >
                    <Icon name="search" className="h-3.5 w-3.5" />
                  </button>
                  {doc.parse_status === "pending" && (
                    <button
                      type="button"
                      className="p-1 rounded-lg hover:bg-bg/60 text-muted hover:text-text"
                      title="Parse"
                      onClick={() => handleParse(doc)}
                    >
                      <Icon name="refresh" className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {viewDoc ? (
        <DocumentViewer
          documentId={viewDoc.document_id}
          filename={viewDoc.filename}
          mime={viewDoc.mime}
          onClose={() => setViewDoc(null)}
        />
      ) : null}
    </div>
  );
}
