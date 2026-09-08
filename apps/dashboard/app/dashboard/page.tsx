import { auth } from "@clerk/nextjs/server";
import Link from "next/link";

import { listBots } from "@/lib/api";
import { createBotAction, deleteBotAction } from "./actions";

export default async function DashboardPage() {
  await auth.protect();

  const bots = await listBots();

  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-12">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Your bots</h1>
        <p className="mt-1 text-sm text-muted">
          Create a bot, train it on your content, and embed it on any site.
        </p>
      </div>

      <form
        action={createBotAction}
        className="mb-10 flex gap-2 rounded-xl border border-border bg-surface p-2"
      >
        <input
          name="name"
          placeholder="Bot name"
          required
          className="flex-1 rounded-lg bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted"
        />
        <button
          type="submit"
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90"
        >
          Create bot
        </button>
      </form>

      {bots.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border p-10 text-center text-sm text-muted">
          No bots yet — create one above.
        </div>
      ) : (
        <ul className="space-y-3">
          {bots.map((bot) => (
            <li
              key={bot.id}
              className="rounded-xl border border-border bg-surface p-4 transition-colors hover:border-accent/40"
            >
              <div className="flex items-center justify-between">
                <Link
                  href={`/dashboard/${bot.id}`}
                  className="font-medium hover:text-accent"
                >
                  {bot.name}
                </Link>
                <form action={deleteBotAction.bind(null, bot.id)}>
                  <button
                    type="submit"
                    className="text-sm text-muted transition-colors hover:text-red-500"
                  >
                    Delete
                  </button>
                </form>
              </div>
              <p className="mt-1 break-all font-mono text-xs text-muted">
                {bot.site_key}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
