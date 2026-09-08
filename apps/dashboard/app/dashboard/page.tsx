import { auth } from "@clerk/nextjs/server";
import Link from "next/link";

import { listBots } from "@/lib/api";
import { createBotAction, deleteBotAction } from "./actions";

function hostOf(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

export default async function DashboardPage() {
  await auth.protect();

  const bots = await listBots();

  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-12">
      <div className="mb-8 flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Your bots</h1>
          <p className="mt-1 text-sm text-muted">
            {bots.length === 0
              ? "Create a bot and train it on your content."
              : `${bots.length} bot${bots.length === 1 ? "" : "s"}`}
          </p>
        </div>

        <details className="group relative">
          <summary className="cursor-pointer list-none rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90 [&::-webkit-details-marker]:hidden">
            New bot
          </summary>
          <form
            action={createBotAction}
            className="absolute right-0 z-10 mt-2 w-80 space-y-3 rounded-xl border border-border bg-surface p-4 shadow-lg"
          >
            <input
              name="name"
              placeholder="Bot name"
              required
              className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted focus:border-accent"
            />
            <input
              name="website_url"
              type="url"
              placeholder="https://your-website.com"
              required
              className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted focus:border-accent"
            />
            <p className="text-xs text-muted">
              We crawl this site to train the bot. You can add more later.
            </p>
            <button
              type="submit"
              className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90"
            >
              Create bot
            </button>
          </form>
        </details>
      </div>

      {bots.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border p-12 text-center text-sm text-muted">
          No bots yet. Use “New bot” to create your first one.
        </div>
      ) : (
        <ul className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-surface">
          {bots.map((bot) => (
            <li
              key={bot.id}
              className="flex items-center justify-between gap-4 px-4 py-3.5 transition-colors hover:bg-surface-muted"
            >
              <Link href={`/dashboard/${bot.id}`} className="min-w-0 flex-1">
                <span className="block truncate font-medium">{bot.name}</span>
                <span className="block truncate text-xs text-muted">
                  {hostOf(bot.website_url)}
                </span>
              </Link>
              <form action={deleteBotAction.bind(null, bot.id)}>
                <button
                  type="submit"
                  className="text-sm text-muted transition-colors hover:text-red-500"
                >
                  Delete
                </button>
              </form>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
