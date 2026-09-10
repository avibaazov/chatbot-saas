"use server";

import { auth } from "@clerk/nextjs/server";
import { revalidatePath } from "next/cache";

import { createBot, deleteBot } from "@/lib/api";

// Render-time gating (protecting the /dashboard page) is not a security boundary on its
// own — a POST can hit a Server Action directly. Every action re-checks auth itself.
// See node_modules/next/dist/docs/01-app/02-guides/server-actions.md § Security.

export type CreateBotState = { ok: boolean; error?: string };

export async function createBotAction(
  _prev: CreateBotState | null,
  formData: FormData,
): Promise<CreateBotState> {
  await auth.protect();

  const name = String(formData.get("name") ?? "").trim();
  const websiteUrl = String(formData.get("website_url") ?? "").trim();
  if (!name) {
    return { ok: false, error: "Bot name is required" };
  }
  if (!websiteUrl) {
    return { ok: false, error: "Website URL is required" };
  }

  try {
    await createBot(name, websiteUrl);
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Could not create bot" };
  }

  revalidatePath("/dashboard");
  return { ok: true };
}

export async function deleteBotAction(botId: string) {
  await auth.protect();
  await deleteBot(botId);
  revalidatePath("/dashboard");
}
