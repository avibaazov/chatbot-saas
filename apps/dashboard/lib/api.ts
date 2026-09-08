/**
 * Server-side client for services/api. Every call attaches the current Clerk session
 * token as a bearer token — the API verifies it (see services/api/app/core/auth.py) and
 * derives the owner from it, so this client never sends a user id directly. Only call
 * these from Server Components / Server Actions, never from the browser (API_BASE_URL is
 * not NEXT_PUBLIC_ on purpose — it's an internal service, not something to expose).
 */

import { auth } from "@clerk/nextjs/server";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8001";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { getToken } = await auth();
  const token = await getToken();
  if (!token) {
    throw new ApiError(401, "Not authenticated");
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...init.headers,
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, body || res.statusText);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export type BotConfig = {
  system_prompt: string;
  model_tier: string;
  display_name: string;
  primary_color: string;
};

export type Bot = {
  id: string;
  name: string;
  config: BotConfig;
  site_key: string;
  allowed_domains: string[];
};

export function listBots(): Promise<Bot[]> {
  return apiFetch<Bot[]>("/bots");
}

export function createBot(name: string): Promise<Bot> {
  return apiFetch<Bot>("/bots", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function deleteBot(botId: string): Promise<void> {
  return apiFetch<void>(`/bots/${botId}`, { method: "DELETE" });
}
