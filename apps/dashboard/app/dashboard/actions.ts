"use server";

import { auth } from "@clerk/nextjs/server";
import { revalidatePath } from "next/cache";

import { createBot, deleteBot } from "@/lib/api";

// Render-time gating (protecting the /dashboard page) is not a security boundary on its
// own — a POST can hit a Server Action directly. Every action re-checks auth itself.
// See node_modules/next/dist/docs/01-app/02-guides/server-actions.md § Security.

export async function createBotAction(formData: FormData) {
  await auth.protect();

  const name = String(formData.get("name") ?? "").trim();
  if (!name) {
    throw new Error("Bot name is required");
  }

  await createBot(name);
  revalidatePath("/dashboard");
}

export async function deleteBotAction(botId: string) {
  await auth.protect();
  await deleteBot(botId);
  revalidatePath("/dashboard");
}
