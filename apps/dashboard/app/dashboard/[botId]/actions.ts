"use server";

import { auth } from "@clerk/nextjs/server";
import { revalidatePath } from "next/cache";

import { reloadDocument, updateBotAppearance } from "@/lib/api";

export async function reloadDocumentAction(botId: string, documentId: string) {
  await auth.protect();

  await reloadDocument(botId, documentId);
  revalidatePath(`/dashboard/${botId}`);
}

export async function updateAppearanceAction(botId: string, formData: FormData) {
  await auth.protect();

  const display_name = String(formData.get("display_name") ?? "").trim();
  const primary_color = String(formData.get("primary_color") ?? "").trim();
  const font_size = String(formData.get("font_size") ?? "").trim();
  if (!display_name) {
    throw new Error("Display name is required");
  }

  await updateBotAppearance(botId, { display_name, primary_color, font_size });
  revalidatePath(`/dashboard/${botId}`);
}
