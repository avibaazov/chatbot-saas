import Link from "next/link";
import { Show, SignUpButton } from "@clerk/nextjs";

const steps = [
  {
    title: "Upload your content",
    body: "Paste docs, FAQs, or help articles. We chunk and embed them into a private vector index — no model training, just seconds.",
  },
  {
    title: "Test the answers",
    body: "Ask questions right in the dashboard. The bot answers only from your material, with retrieval you can inspect.",
  },
  {
    title: "Embed anywhere",
    body: "Copy one script tag onto any site. A domain allow-list and per-bot rate limits keep it locked to where you want it.",
  },
];

const features = [
  {
    title: "Answers from your data",
    body: "Retrieval-augmented generation over your own content, so replies stay grounded instead of guessed.",
  },
  {
    title: "One script tag",
    body: "A tiny vanilla bundle renders the chat bubble on any third-party site — no framework, no cookies.",
  },
  {
    title: "Scoped by design",
    body: "Public site key plus a per-bot domain allow-list, checked server-side on every request.",
  },
  {
    title: "Async ingestion",
    body: "Uploads chunk, embed, and index in the background with a live status your dashboard polls.",
  },
  {
    title: "Bring your models",
    body: "Claude for generation, Voyage or OpenAI for embeddings, MongoDB Atlas Vector Search for storage.",
  },
  {
    title: "Usage you can see",
    body: "Every conversation is logged, so you always know what your bot is being asked and what it costs.",
  },
];

export default function Home() {
  return (
    <main className="flex flex-1 flex-col">
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-border">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 -z-10"
          style={{
            background:
              "radial-gradient(60% 50% at 50% 0%, var(--color-accent-soft), transparent 70%)",
          }}
        />
        <div className="mx-auto w-full max-w-6xl px-6 py-24 text-center sm:py-32">
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-muted">
            RAG chatbots for your website
          </span>
          <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-semibold leading-[1.1] tracking-tight sm:text-6xl">
            Train a chatbot on your content.
            <br />
            <span className="text-accent">Embed it anywhere.</span>
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-lg leading-8 text-muted">
            Upload your docs, get a chatbot that answers from them, and drop it on
            any site with a single script tag.
          </p>
          <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Show when="signed-out">
              <SignUpButton mode="modal">
                <button className="h-12 rounded-full bg-accent px-7 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90">
                  Start building free
                </button>
              </SignUpButton>
            </Show>
            <Show when="signed-in">
              <Link
                href="/dashboard"
                className="flex h-12 items-center rounded-full bg-accent px-7 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90"
              >
                Go to dashboard
              </Link>
            </Show>
            <a
              href="#how-it-works"
              className="flex h-12 items-center rounded-full border border-border px-7 text-sm font-medium transition-colors hover:bg-surface-muted"
            >
              See how it works
            </a>
          </div>

          <div className="mx-auto mt-16 max-w-2xl overflow-hidden rounded-xl border border-border bg-surface text-left shadow-sm">
            <div className="flex items-center gap-1.5 border-b border-border px-4 py-3">
              <span className="h-2.5 w-2.5 rounded-full bg-border" />
              <span className="h-2.5 w-2.5 rounded-full bg-border" />
              <span className="h-2.5 w-2.5 rounded-full bg-border" />
              <span className="ml-3 text-xs text-muted">your-site.com</span>
            </div>
            <pre className="overflow-x-auto p-5 font-mono text-xs leading-6 text-muted">
              <code>{`<script
  src="https://cdn.askbox.dev/widget.js"
  data-bot-key="pk_live_9f2c…"
  data-api-base="https://api.askbox.dev"
  async
></script>`}</code>
            </pre>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="border-b border-border">
        <div className="mx-auto w-full max-w-6xl px-6 py-20">
          <h2 className="text-center text-3xl font-semibold tracking-tight">
            From upload to embed in three steps
          </h2>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {steps.map((step, i) => (
              <div
                key={step.title}
                className="rounded-xl border border-border bg-surface p-6"
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-soft text-sm font-semibold text-accent">
                  {i + 1}
                </span>
                <h3 className="mt-4 font-medium">{step.title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted">{step.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-b border-border">
        <div className="mx-auto w-full max-w-6xl px-6 py-20">
          <h2 className="text-center text-3xl font-semibold tracking-tight">
            Everything the core loop needs
          </h2>
          <div className="mt-12 grid gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <div key={feature.title} className="bg-surface p-6">
                <h3 className="font-medium">{feature.title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted">{feature.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section>
        <div className="mx-auto w-full max-w-6xl px-6 py-24 text-center">
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Ship a support bot this afternoon
          </h2>
          <p className="mx-auto mt-4 max-w-md text-muted">
            Create a bot, upload your first doc, and paste the snippet. No
            infrastructure to run.
          </p>
          <div className="mt-8 flex justify-center">
            <Show when="signed-out">
              <SignUpButton mode="modal">
                <button className="h-12 rounded-full bg-accent px-7 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90">
                  Get started free
                </button>
              </SignUpButton>
            </Show>
            <Show when="signed-in">
              <Link
                href="/dashboard"
                className="flex h-12 items-center rounded-full bg-accent px-7 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90"
              >
                Open your dashboard
              </Link>
            </Show>
          </div>
        </div>
      </section>
    </main>
  );
}
