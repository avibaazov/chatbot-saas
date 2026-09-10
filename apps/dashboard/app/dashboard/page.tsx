import { auth } from "@clerk/nextjs/server";
import Link from "next/link";

import { listBots, listDocuments } from "@/lib/api";
import { createBotAction, deleteBotAction } from "./actions";
import { BotMenu } from "./BotMenu";
import { NewBotForm } from "./NewBotForm";
import { botHealth, StatusBadge } from "./status";

function hostOf(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

function ChatIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8A2.5 2.5 0 0 1 17.5 16H9l-4 4v-4H6.5A2.5 2.5 0 0 1 4 13.5z"
        fill="currentColor"
      />
    </svg>
  );
}

function EmptyState() {
  const steps = [
    ["1", "Add your website", "We crawl it for content to answer from."],
    ["2", "Let it train", "Chunking and indexing runs in the background."],
    ["3", "Embed the snippet", "Drop one script tag on any site."],
  ];
  return (
    <div className="rounded-2xl border border-dashed border-border p-10 text-center">
      <h2 className="text-base font-medium">Create your first chatbot</h2>
      <p className="mx-auto mt-1.5 max-w-md text-sm text-muted">
        Three steps to a working assistant:
      </p>
      <ol className="mx-auto mt-6 grid max-w-2xl gap-3 text-left sm:grid-cols-3">
        {steps.map(([n, title, body]) => (
          <li
            key={n}
            className="rounded-xl border border-border bg-surface p-4"
          >
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent">
              {n}
            </span>
            <p className="mt-2 text-sm font-medium">{title}</p>
            <p className="mt-0.5 text-xs text-muted">{body}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}

export default async function DashboardPage() {
  await auth.protect();

  const bots = await listBots();
  const docs = await Promise.all(
    bots.map((b) => listDocuments(b.id).catch(() => [])),
  );
  const demoSite = bots[0]?.website_url;

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-12">
      <div className="mb-10 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Your chatbots
          </h1>
          <p className="mt-1.5 max-w-prose text-sm text-muted">
            Train an assistant on your website&rsquo;s content and embed it
            anywhere with one script tag.
          </p>
        </div>
        <NewBotForm action={createBotAction} />
      </div>

      {bots.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          <ul className="grid gap-4 sm:grid-cols-2">
            {bots.map((bot, i) => (
              <li
                key={bot.id}
                className="rounded-2xl border border-border bg-surface p-5 transition-colors hover:border-accent/50"
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-soft text-accent">
                    <ChatIcon />
                  </span>
                  <BotMenu
                    botId={bot.id}
                    botName={bot.name}
                    deleteAction={deleteBotAction}
                  />
                </div>

                <Link href={`/dashboard/${bot.id}`} className="mt-3 block">
                  <span className="block font-medium">{bot.name}</span>
                  <span className="mt-0.5 block truncate text-xs text-muted">
                    {hostOf(bot.website_url)}
                  </span>
                </Link>

                <div className="mt-4 flex items-center justify-between">
                  <StatusBadge health={botHealth(docs[i])} />
                  <Link
                    href={`/dashboard/${bot.id}`}
                    className="text-sm font-medium text-accent transition-opacity hover:opacity-80"
                  >
                    Manage &rarr;
                  </Link>
                </div>
              </li>
            ))}
          </ul>

          {demoSite && (
            <section className="mt-10 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-surface p-5">
              <div>
                <h2 className="text-sm font-semibold">See it in action</h2>
                <p className="mt-1 text-xs text-muted">
                  Open a site with the assistant already embedded and try it
                  live.
                </p>
              </div>
              <a
                href={demoSite}
                target="_blank"
                rel="noreferrer"
                className="rounded-lg border border-border px-3.5 py-2 text-sm font-medium text-muted transition-colors hover:border-accent hover:text-foreground"
              >
                Open demo site ↗
              </a>
            </section>
          )}
        </>
      )}
    </div>
  );
}
