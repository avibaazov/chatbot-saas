# AGENTS.md

Guidance for AI coding agents (and humans) working in this repo.

---

## 1. What this product is

A SaaS where a user can **train a chatbot on their own content and embed it on any website**
via a `<script>` tag. Two surfaces:

1. **Dashboard** – user signs in, creates a bot, configures look/behavior, uploads training
   material, gets an embed snippet.
2. **Embeddable widget** – a small JS bundle that renders a chat bubble on the customer's
   third-party site and talks to our API.

This repo is a **fresh rebuild**. A prior prototype (Flask + a hand-rolled bag-of-words
neural net) exists in a separate, archived repo and is not reused — see §2 for why, §4 for
target architecture.

---

## 2. Repo layout (monorepo)

```
chatbot/                        <- GIT REPO ROOT
├── apps/
│   └── dashboard/               Next.js dashboard (Next 16, React 19, TS, Tailwind). Has its
│                                 own AGENTS.md/CLAUDE.md auto-managed by `next dev` — do not
│                                 hand-edit that block, see the note inside it.
├── services/
│   └── api/                     FastAPI backend (not yet scaffolded)
├── packages/
│   └── widget/                  Embeddable chat widget bundle (not yet scaffolded)
├── infra/                       Terraform for MongoDB Atlas etc. (not yet scaffolded)
└── AGENTS.md                    This file — the plan, read first
```

Previous prototype (Flask, bag-of-words model, `testDB.py`, etc.) lived at
`chatbot-deployment/chatbot-deployment/` on this machine and is kept only as a reference —
it is a **separate repo**, not part of this one. Nothing from it is copied in as-is; any
reused idea gets rewritten to match §4/§5 below. Its own `AGENTS.md` there has the full
history of what was wrong with it if you need context.

---

## 3. Hard rules / gotchas

- **Never commit secrets.** All config via environment variables, loaded through one
  `pydantic-settings` module (API) / Next.js env conventions (dashboard). `.env` files are
  local-only and git-ignored (see root `.gitignore`).
- **MongoDB Atlas**: provision a fresh cluster (dedicated tier, backups on), defined in
  `infra/` via Terraform once we get there. No hardcoded connection strings anywhere.
- **Training/ingestion must be async.** Chunk → embed → upsert vectors happens in a
  background job (queue), never inline in a request handler.
- **No process-local shared state.** Anything that needs to survive restarts or work across
  multiple instances goes in Redis or the DB, not an in-memory dict.
- **Widget auth is not cookies.** Public per-bot site key + domain allow-list, checked
  server-side, since the widget runs on third-party domains.
- **Every bot-scoped endpoint must verify the bot belongs to the authenticated user.**
- No literal URLs, keys, or connection strings in code — always config/env.
- `node_modules/` is ignored repo-wide (unrooted pattern in `.gitignore` on purpose, so it
  matches inside every `apps/*`, `services/*`, `packages/*`). Don't re-root it.

---

## 4. Target architecture

Decided direction (no cloud-provider lock-in beyond MongoDB Atlas):

| Concern | Choice |
|---|---|
| Dashboard frontend | **Next.js (`apps/dashboard/`) + TypeScript + Tailwind + shadcn/ui**, deploy on Vercel |
| Dashboard auth | **Clerk** |
| Backend API | **FastAPI** (async, Pydantic validation, OpenAPI) + Uvicorn/Gunicorn, in `services/api/` |
| Bot "brain" | **LLM + RAG** – Claude (Haiku default, Sonnet upgrade tier) via Anthropic API |
| Embeddings | Voyage AI (or OpenAI) embeddings |
| Vector store | **MongoDB Atlas Vector Search** (reuse the one DB, no separate vector DB) |
| Primary DB | **MongoDB Atlas** – dedicated tier (M10+), backups on, provisioned via Terraform (`infra/`) |
| Background jobs | **Redis + a queue** (Arq / RQ / Celery) for doc ingestion + indexing |
| Shared cache / warm state | **Redis** |
| Widget | Tiny **vanilla TS / Preact** bundle (<~30 kb), in `packages/widget/`, served from CDN, params: `bot_id` + public site key |
| Widget auth | Public site key + per-bot domain allow-list + per-bot rate limiting |
| Errors/metrics | Sentry (frontend + backend), plus Atlas monitoring with alerts |
| Payments (later) | Stripe, usage-based (LLM tokens are the cost driver) |

"Training" = **chunk → embed → upsert vectors** (seconds), not gradient descent. No `.pth`
files or pickled model state, anywhere, ever.

Data model: `users` / `bots` / `documents` / `chunks` (vectors) / `conversations`.

---

## 5. Build order

1. ~~Scaffold `apps/dashboard/` (Next.js).~~ Done.
2. Scaffold `services/api/` — FastAPI skeleton, `pydantic-settings` config, health check,
   Mongo connection via env var.
3. Define data model (`users` / `bots` / `documents` / `chunks` / `conversations`) as
   Pydantic models + Mongo indexes.
4. Async ingestion job: upload → chunk → embed → upsert vectors, with a `status` field the
   UI polls. Needs Redis + a queue.
5. RAG inference endpoint: retrieve chunks + call Claude.
6. `packages/widget/` bundle + site-key auth.
7. Wire Clerk into `apps/dashboard/`.
8. Wire dashboard → API (bot CRUD, upload UI, embed snippet generator).
9. Sentry, then Stripe, once the core loop works end to end.

We are currently between steps 1 and 2.

---

## 6. Conventions

- **Python** (`services/api/`): FastAPI + Pydantic models for every request/response. Type
  hints required. No DB calls or blocking work inside request handlers beyond a quick read;
  heavy work → queue. `pytest` for tests; no new code path without a test.
- **Config**: environment variables only, loaded via a single settings module. No literals
  for URLs, keys, or connection strings.
- **Secrets**: never in code, never in git. `.env` local only.
- **TypeScript** (`apps/dashboard/`): follow existing eslint/prettier config; shadcn/ui for
  components; `zod` for form/validation schemas. This is Next 16 — read
  `apps/dashboard/node_modules/next/dist/docs/` before relying on training-data knowledge of
  Next.js APIs, and heed the auto-generated note in `apps/dashboard/AGENTS.md`.
- **Widget** (`packages/widget/`): no heavy framework, no external runtime deps, keep the
  bundle small; all network calls go to the configured API base URL with the public site key.
- **Commits**: conventional-commit style messages; don't commit generated artifacts,
  `node_modules/`, `__pycache__/`, `.pth`, `.next/`, `venv/`.

---

## 7. How to run (current state)

```bash
cd apps/dashboard
npm install
npm run dev                      # http://localhost:3000
```

`services/api/` is not yet scaffolded — nothing to run there yet.

---

## 8. When in doubt

- Don't change code the user hasn't asked you to change.
- If a task touches auth, secrets, or the DB connection, flag it explicitly before acting.
- Before moving or deleting tracked files (especially dependency directories like
  `node_modules`), check how `.gitignore` patterns are rooted so the move doesn't dump
  thousands of newly-untracked files on the user. Rooted (`/x`) patterns only match at the
  path they're declared for; prefer unrooted (`x/`) patterns in a monorepo.
