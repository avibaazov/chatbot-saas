import type { Document } from "@/lib/api";

export type BotHealth = "ready" | "training" | "attention" | "setup";

/** Roll a bot's document statuses up into a single health signal for the UI. */
export function botHealth(docs: Document[]): BotHealth {
  if (docs.length === 0) return "setup";
  if (docs.some((d) => d.status === "failed")) return "attention";
  if (docs.some((d) => d.status === "pending" || d.status === "processing"))
    return "training";
  if (docs.some((d) => d.status === "ready")) return "ready";
  return "setup";
}

const LABEL: Record<BotHealth, string> = {
  ready: "Ready",
  training: "Training",
  attention: "Needs attention",
  setup: "Setup",
};

const STYLE: Record<BotHealth, string> = {
  ready: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  training: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  attention: "bg-red-500/10 text-red-600 dark:text-red-400",
  setup: "bg-surface-muted text-muted",
};

export function StatusBadge({ health }: { health: BotHealth }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${STYLE[health]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {LABEL[health]}
    </span>
  );
}
