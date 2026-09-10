"use client";

import { useState } from "react";

import { WidgetMount } from "./WidgetMount";

/**
 * Opt-in launcher for the real embeddable widget on this page. Off by default so the page
 * isn't covered by a floating chat bubble; when on, it mounts the exact `<script>` a
 * customer would paste, so the user can actually chat with the bot and check its answers.
 */
export function WidgetTester(props: {
  siteKey: string;
  apiBase: string;
  scriptUrl: string;
  offsetBottom?: number;
  reloadKey?: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <section className="rounded-2xl border border-border bg-surface p-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Test your bot</h2>
          <p className="mt-1 text-xs text-muted">
            Loads the real widget in the corner so you can chat and check its
            answers.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-pressed={open}
          className="shrink-0 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:border-accent hover:text-foreground"
        >
          {open ? "Close test" : "Launch widget"}
        </button>
      </div>

      {open && <WidgetMount {...props} />}
    </section>
  );
}
