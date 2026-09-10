import { auth } from "@clerk/nextjs/server";
import Link from "next/link";

import {
  API_BASE_URL,
  getBot,
  listDocuments,
  WIDGET_SCRIPT_URL,
} from "@/lib/api";
import { botHealth, StatusBadge } from "../status";
import { BotWorkspace } from "./BotWorkspace";
import { CopyButton } from "./CopyButton";
import { SourcesPoller } from "./SourcesPoller";
import { WidgetTester } from "./WidgetTester";
import { reloadDocumentAction, updateAppearanceAction } from "./actions";

// How far up the widget sits on this page, so its bubble clears the site footer. Only the
// dashboard tester passes this; real embeds get the default corner position.
const PREVIEW_OFFSET_BOTTOM = 72;

const STATUS_PILL: Record<string, string> = {
  pending: "bg-surface-muted text-muted",
  processing: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  ready: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  failed: "bg-red-500/10 text-red-600 dark:text-red-400",
};

function Spinner() {
  return (
    <svg
      className="h-3.5 w-3.5 animate-spin"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
    >
      <circle
        cx="12"
        cy="12"
        r="9"
        stroke="currentColor"
        strokeWidth="3"
        opacity="0.25"
      />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}

function LivePing() {
  return (
    <span className="relative flex h-2 w-2">
      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-75" />
      <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
    </span>
  );
}

function LinkGlyph() {
  return (
    <svg
      className="h-4 w-4 shrink-0 text-muted"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
    >
      <path
        d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function hostOf(url: string): string | null {
  try {
    return new URL(url).host;
  } catch {
    return null;
  }
}

export default async function BotDetailPage({
  params,
}: PageProps<"/dashboard/[botId]">) {
  await auth.protect();

  const { botId } = await params;
  const [bot, documents] = await Promise.all([
    getBot(botId),
    listDocuments(botId),
  ]);

  const readyCount = documents.filter((d) => d.status === "ready").length;
  const ingesting = documents.some(
    (d) => d.status === "pending" || d.status === "processing",
  );
  const siteDoc = documents.find((d) => d.url && d.url === bot.website_url);
  const host = hostOf(bot.website_url);

  const embedSnippet = `<script
  src="${WIDGET_SCRIPT_URL}"
  data-bot-key="${bot.site_key}"
  data-api-base="${API_BASE_URL}"
  async
></script>`;

  const sources = (
    <section className="overflow-hidden rounded-2xl border border-border bg-surface">
      <div className="flex items-center justify-between gap-3 border-b border-border px-6 py-4">
        <div>
          <h2 className="text-sm font-semibold">Sources</h2>
          <p className="mt-0.5 text-xs text-muted">
            {documents.length === 0
              ? "Nothing ingested yet."
              : `${readyCount} of ${documents.length} trained`}
          </p>
        </div>
        {siteDoc && (
          <form action={reloadDocumentAction.bind(null, botId, siteDoc.id)}>
            <button
              type="submit"
              className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:border-accent hover:text-foreground"
            >
              Refresh content
            </button>
          </form>
        )}
      </div>

      <div className="px-6 py-5">
        {documents.length === 0 ? (
          <p className="text-sm text-muted">
            Ingestion runs in the background after a bot is created — this list
            fills in automatically.
          </p>
        ) : (
          <ul className="space-y-2">
            {documents.map((doc) => (
              <li
                key={doc.id}
                className="flex items-center justify-between gap-3 rounded-lg border border-border bg-surface-muted px-3 py-2.5 text-sm"
              >
                <span className="flex min-w-0 items-center gap-2.5">
                  <LinkGlyph />
                  <span className="min-w-0">
                    <span className="block truncate">
                      {doc.url ?? doc.filename}
                    </span>
                    {doc.error && (
                      <span className="block truncate text-xs text-red-500">
                        {doc.error}
                      </span>
                    )}
                  </span>
                </span>
                <span
                  className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                    STATUS_PILL[doc.status] ?? "bg-surface-muted text-muted"
                  }`}
                >
                  {(doc.status === "pending" ||
                    doc.status === "processing") && <Spinner />}
                  {doc.status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );

  return (
    <div className="mx-auto w-full max-w-6xl space-y-8 px-6 py-10">
      <header className="space-y-3">
        <Link
          href="/dashboard"
          className="text-sm text-muted hover:text-foreground"
        >
          &larr; All bots
        </Link>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">{bot.name}</h1>
          <StatusBadge health={botHealth(documents)} />
          {ingesting && (
            <span className="inline-flex items-center gap-2 text-xs font-medium text-accent">
              <LivePing />
              Training…
            </span>
          )}
          {host && (
            <a
              href={bot.website_url}
              target="_blank"
              rel="noreferrer"
              className="ml-auto rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-muted transition-colors hover:border-accent hover:text-foreground"
            >
              Open demo website ↗
            </a>
          )}
        </div>

        {host && (
          <a
            href={bot.website_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex w-fit items-center gap-1.5 font-mono text-sm text-muted transition-colors hover:text-foreground"
          >
            <LinkGlyph />
            {host}
          </a>
        )}
      </header>

      <BotWorkspace
        action={updateAppearanceAction.bind(null, botId)}
        initial={{
          display_name: bot.config.display_name,
          primary_color: bot.config.primary_color,
          font_size: bot.config.font_size,
        }}
        sources={sources}
        tester={
          <WidgetTester
            siteKey={bot.site_key}
            apiBase={API_BASE_URL}
            scriptUrl={WIDGET_SCRIPT_URL}
            offsetBottom={PREVIEW_OFFSET_BOTTOM}
            reloadKey={`${bot.config.display_name}|${bot.config.primary_color}|${bot.config.font_size}`}
          />
        }
      />

      <details className="group rounded-2xl border border-border bg-surface p-6">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 [&::-webkit-details-marker]:hidden">
          <div>
            <h2 className="flex items-center gap-1.5 text-sm font-semibold">
              <svg
                className="h-3.5 w-3.5 text-muted transition-transform group-open:rotate-90"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden
              >
                <path
                  d="m9 6 6 6-6 6"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Embed on your website
            </h2>
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
          <CopyButton value={embedSnippet} label="Copy code" />
        </summary>

        <pre className="mt-4 overflow-x-auto rounded-lg border border-border bg-surface-muted p-4 font-mono text-xs leading-6">
          {embedSnippet}
        </pre>
      </details>

      <SourcesPoller active={ingesting} />
    </div>
  );
}
