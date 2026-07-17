"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function LegacyHomeRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/");
  }, [router]);

  return <div className="p-6 text-sm text-muted">Redirecting to workspace…</div>;
}
