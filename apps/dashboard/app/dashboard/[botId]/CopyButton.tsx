"use client";

import { type MouseEvent, useState } from "react";

export function CopyButton({
  value,
  label = "Copy",
}: {
  value: string;
  label?: string;
}) {
  const [copied, setCopied] = useState(false);

  async function copy(e: MouseEvent) {
    // The button can live inside a <summary>; don't let the click toggle the <details>.
    e.stopPropagation();
    e.preventDefault();
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard blocked (insecure context / permissions) — nothing useful to do
    }
  }

  return (
    <button
      type="button"
      onClick={copy}
      className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:border-accent hover:text-foreground"
    >
      {copied ? "Copied" : label}
    </button>
  );
}
