"use client";

import Link from "next/link";
import { EmptyState } from "hg_ui_kit";

export default function NotFound() {
  return (
    <main className="p-6 max-w-lg mx-auto">
      <EmptyState
        title="Page not found"
        description="This route is not part of the client workspace. Check the URL or return home."
        actionLabel="Go home"
        onAction={() => {
          window.location.href = "/";
        }}
      />
      <p className="text-sm text-muted mt-4">
        <Link href="/" className="underline">
          Home
        </Link>
      </p>
    </main>
  );
}
