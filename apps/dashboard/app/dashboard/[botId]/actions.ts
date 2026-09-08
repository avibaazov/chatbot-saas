"use server";

import { auth } from "@clerk/nextjs/server";
import { revalidatePath } from "next/cache";

import { askBot, getBot, updateAllowedDomains, uploadDocument } from "@/lib/api";

export async function uploadDocumentAction(botId: string, formData: FormData) {
  await auth.protect();

  const filename = String(formData.get("filename") ?? "").trim();
  const text = String(formData.get("text") ?? "").trim();
  if (!filename || !text) {
    throw new Error("Filename and text are required");
  }

  await uploadDocument(botId, filename, text);
  revalidatePath(`/dashboard/${botId}`);
}

export async function askBotAction(
  botId: string,
  _prevState: { question: string; answer: string | null },
  formData: FormData,
): Promise<{ question: string; answer: string | null }> {
  await auth.protect();

  const question = String(formData.get("question") ?? "").trim();
  if (!question) {
    return { question: "", answer: null };
  }

  const { answer } = await askBot(botId, question);
  return { question, answer };
}

export async function addAllowedDomainAction(botId: string, formData: FormData) {
  await auth.protect();

  const domain = String(formData.get("domain") ?? "").trim();
  if (!domain) {
    throw new Error("Domain is required");
  }

  const bot = await getBot(botId);
  if (!bot.allowed_domains.includes(domain)) {
    await updateAllowedDomains(botId, [...bot.allowed_domains, domain]);
  }
  revalidatePath(`/dashboard/${botId}`);
}

export async function removeAllowedDomainAction(botId: string, domain: string) {
  await auth.protect();

  const bot = await getBot(botId);
  await updateAllowedDomains(
    botId,
    bot.allowed_domains.filter((d) => d !== domain),
  );
  revalidatePath(`/dashboard/${botId}`);
}
