import { auth } from "@clerk/nextjs/server";

import { listBots } from "@/lib/api";
import { createBotAction, deleteBotAction } from "./actions";

export default async function DashboardPage() {
  await auth.protect();

  const bots = await listBots();

  return (
    <div className="mx-auto max-w-2xl p-8">
      <h1 className="mb-6 text-2xl font-semibold">Your bots</h1>

      <form action={createBotAction} className="mb-8 flex gap-2">
        <input
          name="name"
          placeholder="Bot name"
          required
          className="flex-1 rounded border border-black/10 px-3 py-2 dark:border-white/20"
        />
        <button
          type="submit"
          className="rounded bg-black px-4 py-2 text-white dark:bg-white dark:text-black"
        >
          Create bot
        </button>
      </form>

      {bots.length === 0 ? (
        <p className="text-sm text-black/50 dark:text-white/50">
          No bots yet — create one above.
        </p>
      ) : (
        <ul className="space-y-3">
          {bots.map((bot) => (
            <li
              key={bot.id}
              className="rounded border border-black/10 p-4 dark:border-white/20"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">{bot.name}</span>
                <form action={deleteBotAction.bind(null, bot.id)}>
                  <button type="submit" className="text-sm text-red-600">
                    Delete
                  </button>
                </form>
              </div>
              <p className="mt-1 break-all font-mono text-xs text-black/50 dark:text-white/50">
                {bot.site_key}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
