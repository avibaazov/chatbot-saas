"use client";

import { useActionState, useEffect, useRef } from "react";
import { useFormStatus } from "react-dom";

import type { CreateBotState } from "./actions";

const inputClass =
  "w-full rounded-lg border border-border bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted focus:border-accent";

function Spinner() {
  return (
    <svg
      className="h-4 w-4 animate-spin"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
    >
      <circle
        cx="12"
        cy="12"
        r="9"
        stroke="currentColor"
        strokeWidth="3"
        opacity="0.25"
      />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90 disabled:opacity-70"
    >
      {pending && <Spinner />}
      {pending ? "Creating bot…" : "Create bot"}
    </button>
  );
}

export function NewBotForm({
  action,
}: {
  action: (
    prev: CreateBotState | null,
    formData: FormData,
  ) => Promise<CreateBotState>;
}) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const [state, formAction] = useActionState(action, null);

  useEffect(() => {
    if (state?.ok) {
      formRef.current?.reset();
      if (detailsRef.current) detailsRef.current.open = false;
    }
  }, [state]);

  return (
    <details ref={detailsRef} className="group relative">
      <summary className="cursor-pointer list-none rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90 [&::-webkit-details-marker]:hidden">
        + Create chatbot
      </summary>
      <form
        ref={formRef}
        action={formAction}
        className="absolute right-0 z-10 mt-2 w-80 space-y-3 rounded-xl border border-border bg-surface p-4 shadow-lg"
      >
        <input
          name="name"
          placeholder="Bot name"
          required
          className={inputClass}
        />
        <input
          name="website_url"
          type="url"
          placeholder="https://your-website.com"
          required
          className={inputClass}
        />
        <p className="text-xs text-muted">
          We crawl this site to train the bot — this runs in the background
          after the bot is created. You can add more sources later.
        </p>
        {state?.error && <p className="text-xs text-red-500">{state.error}</p>}
        <SubmitButton />
      </form>
    </details>
  );
}
