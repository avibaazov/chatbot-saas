"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * While any source is still pending/processing, re-fetch the server component every few
 * seconds so ingestion status (and the "N of M ready" count) updates without a manual
 * reload. Renders nothing.
 */
export function SourcesPoller({ active }: { active: boolean }) {
  const router = useRouter();

  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => router.refresh(), 3000);
    return () => clearInterval(id);
  }, [active, router]);

  return null;
}
