import { auth } from "@clerk/nextjs/server";

import { getBot, listDocuments } from "@/lib/api";
import { ChatTester } from "./ChatTester";
import { uploadDocumentAction } from "./actions";

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
    </div>
  );
}
