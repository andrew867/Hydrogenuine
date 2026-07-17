"use client";

import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/cn";
import { useKeyRingStore } from "@/store/keyRingStore";
import { env } from "@/lib/env";
import { PersonaPicker } from "@/components/chat/PersonaPicker";

export function NewChatModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (chatId: string) => void;
}) {
  const qc = useQueryClient();
  const [mounted, setMounted] = useState(false);
  const [title, setTitle] = useState("New chat");
  const [fingerprintId, setFingerprintId] = useState<string>("");
  const [skinId, setSkinId] = useState<string>("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { restored, operatorKey, impersonationToken, browserSession, locked } = useKeyRingStore();
  const personaReady = env.demoMode || (restored && !locked && (!!operatorKey || !!impersonationToken || !!browserSession));

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  const { data: personas = [], isLoading: personasLoading, error: personasError } = useQuery({
    queryKey: ["personas"],
    queryFn: () => hgApi.listPersonas(),
    enabled: open && personaReady,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setCreating(true);
    try {
      const res = await hgApi.createChat(title.trim() || "New chat", {
        ...(fingerprintId && { fingerprint_id: fingerprintId }),
        ...(skinId && { skin_id: skinId }),
      });
      void qc.invalidateQueries({ queryKey: ["chats"] });
      setTitle("New chat");
      setFingerprintId("");
      setSkinId("");
      onClose();
      onCreated(res.chat_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create chat");
    } finally {
      setCreating(false);
    }
  };

  const handleClose = () => {
    if (!creating) {
      setError(null);
      onClose();
    }
  };

  if (!open || !mounted) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={handleClose}>
      <div
        className="bg-bg border border-border rounded-2xl shadow-xl w-[min(1100px,96vw)] max-h-[90vh] overflow-y-auto p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">New chat</h2>
          <button
            type="button"
            className="p-2 rounded-xl hover:bg-card/60"
            onClick={handleClose}
            disabled={creating}
            aria-label="Close"
          >
            <Icon name="close" className="w-4 h-4" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-muted mb-1">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-xl bg-card/80 border border-border/70 py-2 px-3 outline-none focus:border-accent/60"
              placeholder="Chat title"
            />
          </div>
          <div>
            <label id="new-chat-persona-label" className="block text-sm font-medium text-muted mb-1" htmlFor="new-chat-persona">
              Persona (optional)
            </label>
            <div id="new-chat-persona" aria-labelledby="new-chat-persona-label">
              <PersonaPicker
                personas={personas}
                fingerprintId={fingerprintId}
                skinId={skinId}
                onFingerprintChange={setFingerprintId}
                onSkinChange={setSkinId}
                loading={personasLoading}
              />
            </div>
            {personasLoading ? <div className="mt-1 text-xs text-muted">Loading factory personas…</div> : null}
            {!personasLoading && personasError ? <div className="mt-1 text-xs text-red-500">Could not load personas.</div> : null}
            {!personasLoading && !personasError && personaReady && personas.length === 0 ? (
              <div className="mt-1 text-xs text-muted">No personas available for this tenant.</div>
            ) : null}
          </div>
          {error && <div className="text-sm text-red-500">{error}</div>}
          <div className="flex gap-2 justify-end pt-2">
            <button
              type="button"
              className={cn("rounded-xl px-4 py-2 border border-border/70", "hover:bg-card/60")}
              onClick={handleClose}
              disabled={creating}
            >
              Cancel
            </button>
            <button
              type="submit"
              className={cn("rounded-xl px-4 py-2 bg-accent text-accent-fg", "hover:opacity-90 disabled:opacity-50")}
              disabled={creating}
            >
              {creating ? "Creating…" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}
