import { auth } from "@clerk/nextjs/server";
import Link from "next/link";

import { API_BASE_URL, getBot, listDocuments, WIDGET_SCRIPT_URL } from "@/lib/api";
import { CopyButton } from "./CopyButton";
import { WidgetMount } from "./WidgetMount";
import { reloadDocumentAction, updateAppearanceAction } from "./actions";

// How far up the widget sits on this page, so its bubble clears the site footer. Only the
// dashboard preview passes this; real embeds get the default corner position.
const PREVIEW_OFFSET_BOTTOM = 72;

const fieldClass =
  "w-full rounded-lg border border-border bg-transparent px-3 py-2 text-sm outline-none focus:border-accent";

const STATUS_PILL: Record<string, string> = {
  pending: "bg-surface-muted text-muted",
  processing: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  ready: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  failed: "bg-red-500/10 text-red-600 dark:text-red-400",
};

function hostOf(url: string): string | null {
  try {
    return new URL(url).host;
  } catch {
    return null;
  }
}

export default async function BotDetailPage({ params }: PageProps<"/dashboard/[botId]">) {
  await auth.protect();

  const { botId } = await params;
  const [bot, documents] = await Promise.all([getBot(botId), listDocuments(botId)]);

  const readyCount = documents.filter((d) => d.status === "ready").length;
  const siteDoc = documents.find((d) => d.url && d.url === bot.website_url);
  const host = hostOf(bot.website_url);

  const embedSnippet = `<script
  src="${WIDGET_SCRIPT_URL}"
  data-bot-key="${bot.site_key}"
  data-api-base="${API_BASE_URL}"
  async
></script>`;

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 px-6 py-10">
      <header className="space-y-2">
        <Link href="/dashboard" className="text-sm text-muted hover:text-foreground">
          ← All bots
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight">{bot.name}</h1>
        <p className="text-sm text-muted">
          {documents.length === 0
            ? "No sources yet."
            : `${readyCount} of ${documents.length} source${
                documents.length === 1 ? "" : "s"
              } ready`}
          {" · "}
          <span>live preview in the bottom-right corner</span>
        </p>
      </header>

      <section className="rounded-2xl border border-border bg-surface p-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold">Sources</h2>
          {siteDoc && (
            <form action={reloadDocumentAction.bind(null, botId, siteDoc.id)}>
              <button
                type="submit"
                className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:border-accent hover:text-foreground"
              >
                Re-crawl
              </button>
            </form>
          )}
        </div>

        {documents.length === 0 ? (
          <p className="text-sm text-muted">
            Nothing ingested yet — ingestion runs in the background after a bot is created.
          </p>
        ) : (
          <ul className="space-y-2">
            {documents.map((doc) => (
              <li
                key={doc.id}
                className="flex items-center justify-between gap-3 rounded-lg border border-border bg-surface-muted px-3 py-2 text-sm"
              >
                <span className="min-w-0">
                  <span className="block truncate">{doc.url ?? doc.filename}</span>
                  {doc.error && (
                    <span className="block truncate text-xs text-red-500">{doc.error}</span>
                  )}
                </span>
                <span
                  className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                    STATUS_PILL[doc.status] ?? "bg-surface-muted text-muted"
                  }`}
                >
                  {doc.status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-2xl border border-border bg-surface p-6">
        <h2 className="mb-4 text-sm font-semibold">Appearance</h2>

        <form
          action={updateAppearanceAction.bind(null, botId)}
          className="grid gap-4 sm:grid-cols-3"
        >
          <label className="flex flex-col gap-1.5 text-xs font-medium text-muted sm:col-span-1">
            Display name
            <input
              name="display_name"
              defaultValue={bot.config.display_name}
              maxLength={40}
              required
              className={fieldClass}
            />
          </label>

          <label className="flex flex-col gap-1.5 text-xs font-medium text-muted">
            Primary color
            <input
              name="primary_color"
              type="color"
              defaultValue={bot.config.primary_color}
              className="h-9 w-full cursor-pointer rounded-lg border border-border bg-transparent px-1"
            />
          </label>

          <label className="flex flex-col gap-1.5 text-xs font-medium text-muted">
            Font size
            <select name="font_size" defaultValue={bot.config.font_size} className={fieldClass}>
              <option value="small">Small</option>
              <option value="medium">Medium</option>
              <option value="large">Large</option>
            </select>
          </label>

          <div className="sm:col-span-3">
            <button
              type="submit"
              className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90"
            >
              Save
            </button>
          </div>
        </form>
      </section>

      <section className="rounded-2xl border border-border bg-surface p-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">Embed</h2>
            <p className="mt-1 text-xs text-muted">
              Paste before <code>&lt;/body&gt;</code>
              {host && (
                <>
                  {" "}
                  on <span className="font-mono">{host}</span>
                </>
              )}
              .
            </p>
          </div>
          <CopyButton value={embedSnippet} label="Copy" />
        </div>

        <pre className="overflow-x-auto rounded-lg border border-border bg-surface-muted p-4 font-mono text-xs leading-6">
          {embedSnippet}
        </pre>
      </section>

      <WidgetMount
        siteKey={bot.site_key}
        apiBase={API_BASE_URL}
        scriptUrl={WIDGET_SCRIPT_URL}
        offsetBottom={PREVIEW_OFFSET_BOTTOM}
        reloadKey={`${bot.config.display_name}|${bot.config.primary_color}|${bot.config.font_size}`}
      />
    </div>
  );
}
