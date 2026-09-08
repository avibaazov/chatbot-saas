# Roadmap / project status

Status of the rebuild against the build order in [`AGENTS.md`](AGENTS.md) §5.
Legend: ✅ done · 🟡 works but is a known shortcut · ❌ not started.

_Last reviewed: 2026-09-08._

---

## Snapshot

| Area | State |
|---|---|
| Monorepo scaffold (`apps/` · `services/` · `packages/` · `infra/`) | ✅ |
| Dashboard (Next 16 / React 19 / Tailwind v4) | ✅ core flows |
| Dashboard auth (Clerk) | ✅ |
| FastAPI backend skeleton + config + Mongo | ✅ |
| Data model (`users` / `bots` / `documents` / `chunks` / `conversations`) | ✅ models, 🟡 `conversations` unused |
| Bot CRUD + ownership checks | ✅ |
| Doc ingestion (chunk → embed → upsert + status) | ✅ pipeline, 🟡 runs inline |
| RAG inference endpoint (retrieve → Claude) | ✅ logic, 🟡 brute-force retrieval |
| Real Claude / Voyage providers | ✅ with fake fallbacks |
| Embeddable widget + site-key auth | ✅ |
| Background queue (Redis) | ❌ |
| Vector search (Atlas) | ❌ (Python cosine scan today) |
| `infra/` Terraform | ❌ (stub README) |
| CI | ❌ (no `.github/`) |
| Deployment config | ❌ |
| Sentry | ❌ |
| Stripe / billing / usage metering | ❌ |

---

## Done (✅)

**Step 1 – Dashboard scaffold**
- Landing page, shared header/footer, dark-mode tokens, "Askbox" branding.
- Sign-in / sign-up routes, `ClerkProvider`, `proxy.ts` running `clerkMiddleware()`.

**Step 2 – FastAPI skeleton**
- `app/main.py` with split sub-apps (`dashboard_app` + mounted `widget_app`) so widget CORS is per-bot.
- `pydantic-settings` config module — the only place env vars are read.
- `motor` Mongo client (lazy singleton); classic indexes created on startup.
- `GET /health`.

**Step 3 – Data model**
- Pydantic models for all five collections + `ObjectId` helpers.
- Indexes for `users`, `bots`, `documents`, `chunks`, `conversations`.

**Step 4 – Ingestion pipeline**
- `chunk_text` → `embeddings.embed` → `chunks.insert_many`, with a `status` field the dashboard polls (`pending` / `processing` / `ready` / `failed`).
- Text ingestion and single-page URL ingestion (`ingest_url`), plus a `/reload` endpoint to re-crawl.
- URL fetch has an SSRF guard (public hosts only, per-hop redirect re-validation, size/content-type caps) and `trafilatura` main-content extraction.
- `VoyageEmbeddingsProvider` (real) with `FakeEmbeddingsProvider` fallback.

**Step 5 – RAG inference**
- `POST /bots/{bot_id}/ask` (dashboard, Clerk-auth) and `POST /widget/{site_key}/ask` (public).
- `answer_question`: embed question → retrieve top-k chunks → Claude with a grounding system prompt.
- `ClaudeProvider` (Haiku default / Sonnet tier via `model_tier`) with `FakeLLMProvider` fallback.

**Step 6 – Widget**
- Vanilla TS, Shadow DOM, esbuild IIFE bundle, no runtime deps.
- `GET /config` + `POST /ask`; per-bot CORS computed from `allowed_domains`; exact-host + subdomain match; first-party dashboard origin always allowed.
- In-memory fixed-window rate limit (20/min per site key).
- Appearance: `primary_color`, `font_size`; `data-open` / `data-offset-bottom` for the dashboard live preview.

**Step 7 – Clerk in dashboard** — `ClerkProvider`, middleware, `auth.protect()` in every server action / page.

**Step 8 – Dashboard ↔ API**
- Bot list / create (name + `website_url`, auto-crawled on create) / delete.
- Bot detail: sources list with status pills, re-crawl, appearance form, embed-snippet generator + copy button, **live widget preview** (`WidgetMount`).
- API JWT verification against Clerk JWKS (RS256), stateless.

**Tests** — ~87 tests across 12 files (`pytest` + `pytest-asyncio`), covering auth, bots, documents, widget, ingestion, RAG, web-fetch, domains, models, embeddings, llm, health.
_(Not runnable in every environment — `pytest` must be installed via `pip install -e ".[dev]"`.)_

---

## Known shortcuts — flagged in code, not production-ready (🟡)

| # | Shortcut | Where | What "done" looks like |
|---|---|---|---|
| 1 | **Ingestion runs inline in the request** — `InMemoryQueue.enqueue` just `await`s the job. No worker, no retries, no persistence. `get_queue` raises `NotImplementedError` if `REDIS_URL` is set. | `app/services/queue.py` | Redis + Arq/RQ/Celery worker; request returns immediately with `status=pending`. |
| 2 | **Retrieval is an O(n) Python cosine scan** — loads every chunk for a bot from Mongo per query. `AtlasVectorStore` is a `NotImplementedError` stub. | `app/services/retrieval.py` | Atlas Vector Search index on `chunks.embedding` + `$vectorSearch` aggregation. |
| 3 | **Rate limiter is process-local** — in-memory dict, lost on restart, not shared across instances. | `app/services/rate_limit.py` | Redis `INCR` + `EXPIRE`, same signature. |
| 4 | **Fake providers silently used when keys absent** — `FakeEmbeddingsProvider` / `FakeLLMProvider`; retrieval quality on fake vectors is meaningless. | `embeddings.py`, `llm.py` | Fail loudly (or a clear dev banner) when a real key is expected. |
| 5 | **`conversations` collection is never written** — model + indexes exist; no chat history, no analytics, no transcript view. | `app/models/conversation.py` | Persist each widget turn; surface transcripts in the dashboard. |
| 6 | **No response streaming** — widget blocks until the full answer returns. | `widget.ts`, `routes/widget.py` | SSE / chunked streaming from the `/ask` endpoints. |
| 7 | **Ingestion sources are thin** — paste-text or single URL only. No file upload (PDF/DOCX), no crawl/sitemap, no re-chunk on model change. | `routes/documents.py` | File upload + storage; multi-page crawl; sitemap ingest. |
| 8 | **Widget bundle isn't published anywhere** — `dist/widget.js` is git-ignored; `WIDGET_SCRIPT_URL` defaults to a local `http.server`. No CDN/hosting story. | `packages/widget`, `lib/api.ts` | Build + publish to a CDN; embed snippet points at it. |
| 9 | **Bot behavior isn't editable** — `system_prompt` and `model_tier` (the Sonnet upgrade tier) are set at model defaults; the dashboard only edits appearance. | `routes/bots.py` (`UpdateAppearanceRequest` comment) | A "Behavior" form: prompt + model tier. |
| 10 | Index creation is skipped when `MONGODB_URI` is unset (so the app boots for local/health-check use). | `app/main.py` lifespan | Fine for dev; note it for deploy. |

---

## Not started (❌)

### Infrastructure & ops
- **`infra/` Terraform** — only a stub README. Atlas cluster (M10+, backups), Vector Search index, Redis, DB users, network access are all manual today. (`AGENTS.md §3/§4`.)
- **Redis** — needed for the queue (#1) and shared cache/warm state (`AGENTS.md §4`).
- **CI** — no `.github/`. Nothing runs lint / typecheck / `pytest` / `next build` on push.
- **Deployment config** — no Vercel project config, no Dockerfile / Procfile / gunicorn setup for the API, no environment matrix (dev/staging/prod).
- **Atlas monitoring + alerts** (`AGENTS.md §4`).

### Product / platform
- **Sentry** — frontend + backend error/perf (`AGENTS.md §5` step 9).
- **Stripe** — usage-based billing; LLM-token cost driver (`AGENTS.md §5` step 9).
- **Usage metering** — no token/request counting per bot or per user; prerequisite for Stripe and for plan quotas.
- **Plan / quota enforcement** — rate limit is a hardcoded 20/min for everyone; no per-plan limits, no monthly caps.
- **Conversation analytics / dashboard** — depends on #5.
- **Widget polish** — conversation continuity across reloads, unread indicator, richer a11y, retry on network error.

### Housekeeping
- **No root `README.md`** (only `AGENTS.md` / `CLAUDE.md`).
- `services/api/README.md` "Layout" section is stale — lists `health.py` only, omits most of `app/`.
- **Large uncommitted working set** — the dashboard redesign, the appearance feature, and `website_url` on `Bot` are unstaged; `CopyButton.tsx`, `WidgetMount.tsx`, and `app/services/ingestion_jobs.py` are untracked. `ingestion_jobs.py` is imported by the modified routes, so the tree won't run until it's committed. Branch is ahead of `origin/master` by 1 commit.

---

## Suggested next steps (in order)

1. **Commit the working set** (incl. `ingestion_jobs.py`) so `master` is coherent again.
2. **Add CI** — lint + typecheck + `pytest` + `next build` on PR. Cheap, unblocks everything else.
3. **Redis + real queue** (shortcut #1) — the biggest gap between "demo" and "product"; also fixes the rate limiter (#3).
4. **`infra/` Terraform** for Atlas (cluster + Vector Search index) + Redis, then wire `AtlasVectorStore` (#2).
5. **Deployment**: Vercel for the dashboard, a container + gunicorn for the API.
6. **Usage metering → Sentry → Stripe** (`AGENTS.md §5` step 9), once the core loop runs on real infra.
