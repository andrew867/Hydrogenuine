import Link from "next/link";

export default function OfflinePage() {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-lg flex-col items-center justify-center gap-4 p-8 text-center">
      <h1 className="text-2xl font-semibold">You are offline</h1>
      <p className="text-muted">
        Hydrogenuine needs a network connection for live chat, approvals, and operator surfaces.
        Cached shell is available; reconnect to continue working.
      </p>
      <Link
        href="/"
        className="rounded-xl border border-accent/40 bg-accent/10 px-4 py-2 text-sm font-medium hover:bg-accent/20"
      >
        Return home
      </Link>
    </div>
  );
}
