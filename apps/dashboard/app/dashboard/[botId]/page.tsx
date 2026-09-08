import { auth } from "@clerk/nextjs/server";

import { API_BASE_URL, getBot, listDocuments, WIDGET_SCRIPT_URL } from "@/lib/api";
import { ChatTester } from "./ChatTester";
import {
  addAllowedDomainAction,
  removeAllowedDomainAction,
  uploadDocumentAction,
} from "./actions";

const STATUS_COLOR: Record<string, string> = {
  pending: "text-black/50 dark:text-white/50",
  processing: "text-yellow-600",
  ready: "text-green-600",
  failed: "text-red-600",
};

export default async function BotDetailPage({ params }: PageProps<"/dashboard/[botId]">) {
  await auth.protect();

  const { botId } = await params;
  const [bot, documents] = await Promise.all([getBot(botId), listDocuments(botId)]);
  const boundUpload = uploadDocumentAction.bind(null, botId);
  const boundAddDomain = addAllowedDomainAction.bind(null, botId);

  const embedSnippet = `<script
  src="${WIDGET_SCRIPT_URL}"
  data-bot-key="${bot.site_key}"
  data-api-base="${API_BASE_URL}"
  async
></script>`;

  return (
    <div className="mx-auto max-w-2xl space-y-8 p-8">
      <div>
        <h1 className="text-2xl font-semibold">{bot.name}</h1>
        <p className="mt-1 break-all font-mono text-xs text-black/50 dark:text-white/50">
          site key: {bot.site_key}
        </p>
      </div>

      <section>
        <h2 className="mb-3 font-medium">Training material</h2>
        <form action={boundUpload} className="mb-4 space-y-2">
          <input
            name="filename"
            placeholder="Filename (e.g. faq.txt)"
            required
            className="w-full rounded border border-black/10 px-3 py-2 dark:border-white/20"
          />
          <textarea
            name="text"
            placeholder="Paste the content to train on…"
            required
            rows={4}
            className="w-full rounded border border-black/10 px-3 py-2 dark:border-white/20"
          />
          <button
            type="submit"
            className="rounded bg-black px-4 py-2 text-white dark:bg-white dark:text-black"
          >
            Upload
          </button>
        </form>

        {documents.length === 0 ? (
          <p className="text-sm text-black/50 dark:text-white/50">No documents uploaded yet.</p>
        ) : (
          <ul className="space-y-2">
            {documents.map((doc) => (
              <li
                key={doc.id}
                className="flex items-center justify-between rounded border border-black/10 px-3 py-2 text-sm dark:border-white/20"
              >
                <span>{doc.filename}</span>
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
        <p className="mb-3 text-sm text-black/50 dark:text-white/50">
          The embed snippet below only works from these domains — the API checks the
          request&apos;s origin against this list before answering.
        </p>
        <form action={boundAddDomain} className="mb-3 flex gap-2">
          <input
            name="domain"
            placeholder="example.com or localhost:3000"
            required
            className="flex-1 rounded border border-black/10 px-3 py-2 text-sm dark:border-white/20"
          />
          <button
            type="submit"
            className="rounded bg-black px-4 py-2 text-sm text-white dark:bg-white dark:text-black"
          >
            Add
          </button>
        </form>

        {bot.allowed_domains.length === 0 ? (
          <p className="text-sm text-black/50 dark:text-white/50">
            No domains allowed yet — the widget won&apos;t respond anywhere until you add one.
          </p>
        ) : (
          <ul className="space-y-2">
            {bot.allowed_domains.map((domain) => (
              <li
                key={domain}
                className="flex items-center justify-between rounded border border-black/10 px-3 py-2 text-sm dark:border-white/20"
              >
                <span className="font-mono">{domain}</span>
                <form action={removeAllowedDomainAction.bind(null, botId, domain)}>
                  <button type="submit" className="text-red-600">
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
        <pre className="overflow-x-auto rounded bg-black/5 p-3 text-xs dark:bg-white/10">
          {embedSnippet}
        </pre>
      </section>
    </div>
  );
}
