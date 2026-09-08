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
    <div className="rounded border border-black/10 p-4 dark:border-white/20">
      <h2 className="mb-3 font-medium">Test chat</h2>
      <form action={formAction} className="flex gap-2">
        <input
          name="question"
          placeholder="Ask your bot something…"
          required
          className="flex-1 rounded border border-black/10 px-3 py-2 dark:border-white/20"
        />
        <button
          type="submit"
          disabled={isPending}
          className="rounded bg-black px-4 py-2 text-white disabled:opacity-50 dark:bg-white dark:text-black"
        >
          {isPending ? "Asking…" : "Ask"}
        </button>
      </form>
      {state.answer !== null && (
        <div className="mt-3 rounded bg-black/5 p-3 text-sm dark:bg-white/10">
          <p className="text-black/50 dark:text-white/50">Q: {state.question}</p>
          <p className="mt-1">{state.answer}</p>
        </div>
      )}
    </div>
  );
}
