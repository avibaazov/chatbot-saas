import { auth } from "@clerk/nextjs/server";
import Link from "next/link";

import { API_BASE_URL, getBot, listDocuments, WIDGET_SCRIPT_URL } from "@/lib/api";
import { ChatTester } from "./ChatTester";
import {
  addAllowedDomainAction,
  ingestUrlAction,
  removeAllowedDomainAction,
  uploadDocumentAction,
} from "./actions";

const STATUS_COLOR: Record<string, string> = {
  pending: "text-muted",
  processing: "text-amber-500",
  ready: "text-emerald-500",
  failed: "text-red-500",
};

export default async function BotDetailPage({ params }: PageProps<"/dashboard/[botId]">) {
  await auth.protect();

  const { botId } = await params;
  const [bot, documents] = await Promise.all([getBot(botId), listDocuments(botId)]);
  const boundUpload = uploadDocumentAction.bind(null, botId);
  const boundIngestUrl = ingestUrlAction.bind(null, botId);
  const boundAddDomain = addAllowedDomainAction.bind(null, botId);

  const embedSnippet = `<script
  src="${WIDGET_SCRIPT_URL}"
  data-bot-key="${bot.site_key}"
  data-api-base="${API_BASE_URL}"
  async
></script>`;

  return (
    <div className="mx-auto w-full max-w-3xl space-y-10 px-6 py-12">
      <div>
        <Link href="/dashboard" className="text-sm text-muted hover:text-foreground">
          ← All bots
        </Link>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">{bot.name}</h1>
        <p className="mt-1 break-all font-mono text-xs text-muted">
          site key: {bot.site_key}
        </p>
      </div>

      <section>
        <h2 className="mb-3 font-medium">Training material</h2>

        <form
          action={boundIngestUrl}
          className="mb-3 space-y-2 rounded-xl border border-border bg-surface p-4"
        >
          <p className="text-sm font-medium">Train on a website</p>
          <p className="text-xs text-muted">
            We fetch the page, pull out the readable text, and index it. Pages that render
            with JavaScript may not have extractable content.
          </p>
          <div className="flex gap-2">
            <input
              name="url"
              type="url"
              placeholder="https://example.com/faq"
              required
              className="flex-1 rounded-lg border border-border bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted focus:border-accent"
            />
            <button
              type="submit"
              className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90"
            >
              Fetch &amp; train
            </button>
          </div>
        </form>

        <form
          action={boundUpload}
          className="mb-4 space-y-2 rounded-xl border border-border bg-surface p-4"
        >
          <p className="text-sm font-medium">Paste text</p>
          <input
            name="filename"
            placeholder="Filename (e.g. faq.txt)"
            required
            className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted focus:border-accent"
          />
          <textarea
            name="text"
            placeholder="Paste the content to train on…"
            required
            rows={4}
            className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted focus:border-accent"
          />
          <button
            type="submit"
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90"
          >
            Upload
          </button>
        </form>

        {documents.length === 0 ? (
          <p className="text-sm text-muted">No documents added yet.</p>
        ) : (
          <ul className="space-y-2">
            {documents.map((doc) => (
              <li
                key={doc.id}
                className="flex items-center justify-between gap-3 rounded-lg border border-border bg-surface px-3 py-2 text-sm"
              >
                <span className="min-w-0">
                  <span className="block truncate">{doc.filename}</span>
                  {doc.url && (
                    <span className="block truncate text-xs text-muted">{doc.url}</span>
                  )}
                  {doc.error && (
                    <span className="block truncate text-xs text-red-500">{doc.error}</span>
                  )}
                </span>
                <span className={STATUS_COLOR[doc.status] ?? ""}>{doc.status}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <ChatTester botId={botId} />
      </section>

      <section>
        <h2 className="mb-3 font-medium">Allowed domains</h2>
        <p className="mb-3 text-sm text-muted">
          The embed snippet below only works from these domains — the API checks the
          request&apos;s origin against this list before answering.
        </p>
        <form action={boundAddDomain} className="mb-3 flex gap-2">
          <input
            name="domain"
            placeholder="example.com or localhost:3000"
            required
            className="flex-1 rounded-lg border border-border bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted focus:border-accent"
          />
          <button
            type="submit"
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90"
          >
            Add
          </button>
        </form>

        {bot.allowed_domains.length === 0 ? (
          <p className="text-sm text-muted">
            No domains allowed yet — the widget won&apos;t respond anywhere until you add one.
          </p>
        ) : (
          <ul className="space-y-2">
            {bot.allowed_domains.map((domain) => (
              <li
                key={domain}
                className="flex items-center justify-between rounded-lg border border-border bg-surface px-3 py-2 text-sm"
              >
                <span className="font-mono">{domain}</span>
                <form action={removeAllowedDomainAction.bind(null, botId, domain)}>
                  <button
                    type="submit"
                    className="text-muted transition-colors hover:text-red-500"
                  >
                    Remove
                  </button>
                </form>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="mb-3 font-medium">Embed on your site</h2>
        <pre className="overflow-x-auto rounded-xl border border-border bg-surface-muted p-4 font-mono text-xs leading-6">
          {embedSnippet}
        </pre>
      </section>
    </div>
  );
}
