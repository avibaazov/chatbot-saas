"use client";

import { useEffect, useRef } from "react";

/**
 * Per-bot overflow menu (the "⋯" on a bot card). Keeps destructive actions out of the
 * card's primary surface; Delete asks for confirmation before the Server Action fires.
 */
export function BotMenu({
  botId,
  botName,
  deleteAction,
}: {
  botId: string;
  botName: string;
  deleteAction: (botId: string) => Promise<void>;
}) {
  const ref = useRef<HTMLDetailsElement>(null);

  // Close the menu on outside click / Escape.
  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node))
        ref.current.open = false;
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && ref.current) ref.current.open = false;
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  return (
    <details ref={ref} className="relative">
      <summary className="flex h-8 w-8 cursor-pointer list-none items-center justify-center rounded-lg text-muted transition-colors hover:bg-surface-muted hover:text-foreground [&::-webkit-details-marker]:hidden">
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="currentColor"
          aria-hidden
        >
          <circle cx="12" cy="5" r="1.7" />
          <circle cx="12" cy="12" r="1.7" />
          <circle cx="12" cy="19" r="1.7" />
        </svg>
        <span className="sr-only">Actions for {botName}</span>
      </summary>
      <div className="absolute right-0 z-20 mt-1 w-44 rounded-lg border border-border bg-surface p-1 shadow-lg">
        <form
          action={deleteAction.bind(null, botId)}
          onSubmit={(e) => {
            if (!confirm(`Delete “${botName}”? This can’t be undone.`))
              e.preventDefault();
          }}
        >
          <button
            type="submit"
            className="w-full rounded-md px-2.5 py-1.5 text-left text-sm text-red-500 transition-colors hover:bg-red-500/10"
          >
            Delete bot
          </button>
        </form>
      </div>
    </details>
  );
}
