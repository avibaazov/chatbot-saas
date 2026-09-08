"use client";

import { useActionState } from "react";

import { askBotAction } from "./actions";

type State = { question: string; answer: string | null };

export function ChatTester({ botId }: { botId: string }) {
  const boundAction = askBotAction.bind(null, botId);
  const [state, formAction, isPending] = useActionState<State, FormData>(boundAction, {
    question: "",
    answer: null,
  });

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <h2 className="mb-3 font-medium">Test chat</h2>
      <form action={formAction} className="flex gap-2">
        <input
          name="question"
          placeholder="Ask your bot something…"
          required
          className="flex-1 rounded-lg border border-border bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted focus:border-accent"
        />
        <button
          type="submit"
          disabled={isPending}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {isPending ? "Asking…" : "Ask"}
        </button>
      </form>
      {state.answer !== null && (
        <div className="mt-3 rounded-lg bg-surface-muted p-3 text-sm">
          <p className="text-muted">Q: {state.question}</p>
          <p className="mt-1">{state.answer}</p>
        </div>
      )}
    </div>
  );
}
