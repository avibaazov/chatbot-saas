# Roadmap / project status

Status of the rebuild against the build order in [`AGENTS.md`](AGENTS.md) §5.
Legend: ✅ done · 🟡 works but is a known shortcut · ❌ not started.

_Last reviewed: 2026-09-08. Stripe / paid billing is out of scope for this project._

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
| Doc ingestion (chunk → embed → upsert + status) | ✅ pipeline; inline by default, background task via `INGEST_INLINE=false` |
| RAG inference endpoint (retrieve → Claude) | ✅ logic, 🟡 brute-force retrieval |
| Real Claude / Voyage providers | ✅ with fake fallbacks |
| Embeddable widget + site-key auth | ✅ |
| Widget bundle hosting | ✅ served by the API at `GET /widget.js` |
| Document size cap | ✅ 100k chars per paste |
| Durable background queue (Redis) | ❌ (background task is in-process, dies on restart) |
| Vector search (Atlas) | ❌ (Python cosine scan today) |
| `infra/` Terraform | ❌ (stub README) |
| CI | ❌ (no `.github/`) |
| Deployment config | ❌ |
| Sentry / error logging | ❌ |

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
- Text ingestion (capped at 100k chars) and single-page URL ingestion (`ingest_url`), plus a `/reload` endpoint to re-crawl.
- URL fetch has an SSRF guard (public hosts only, per-hop redirect re-validation, size/content-type caps) and `trafilatura` main-content extraction.
- `VoyageEmbeddingsProvider` (real) with `FakeEmbeddingsProvider` fallback.
- `INGEST_INLINE` toggles between awaiting the job in-request (default) and running it as a background task (`status=pending` returned immediately). See shortcut #1 for what's still missing.

**Step 5 – RAG inference**
- `POST /bots/{bot_id}/ask` (dashboard, Clerk-auth) and `POST /widget/{site_key}/ask` (public).
- `answer_question`: embed question → retrieve top-k chunks → Claude with a grounding system prompt.
- `ClaudeProvider` (Haiku default / Sonnet tier via `model_tier`) with `FakeLLMProvider` fallback.

**Step 6 – Widget**
- Vanilla TS, Shadow DOM, esbuild IIFE bundle (~4 KB), no runtime deps.
- Served by the API at `GET /widget.js` (from `WIDGET_BUNDLE_PATH`, default = monorepo build output) with `Access-Control-Allow-Origin: *` and a short cache; the dashboard embed snippet points there by default.
- `GET /config` + `POST /ask`; per-bot CORS computed from `allowed_domains`; exact-host + subdomain match; first-party dashboard origin always allowed.
- In-memory fixed-window rate limit (20/min per site key).
- Appearance: `primary_color`, `font_size`; `data-open` / `data-offset-bottom` for the dashboard live preview.

**Step 7 – Clerk in dashboard** — `ClerkProvider`, middleware, `auth.protect()` in every server action / page.

**Step 8 – Dashboard ↔ API**
- Bot list / create (name + `website_url`, auto-crawled on create) / delete.
- Bot detail: sources list with status pills, re-crawl, appearance form, embed-snippet generator + copy button, **live widget preview** (`WidgetMount`).
- API JWT verification against Clerk JWKS (RS256), stateless.

**Tests** — 91 tests across 12 files (`pytest` + `pytest-asyncio`), covering auth, bots, documents, widget, ingestion, RAG, web-fetch, domains, models, embeddings, llm, health. The bots / documents / widget / chat / auth suites hit a live Atlas cluster (`MONGODB_URI` from `.env`) and take several minutes.
_(`test_rate_limit_kicks_in_after_threshold` is flaky in the full-suite run — see shortcut #3.)_

---

## Known shortcuts — flagged in code, not production-ready (🟡)

| # | Shortcut | Where | What "done" looks like |
|---|---|---|---|
| 1 | **Background ingestion isn't durable** — with `INGEST_INLINE=false` the job runs as an in-process `BackgroundTasks` task (request returns `status=pending` immediately), but there's still no worker, no retries, and a restart mid-job leaves a document stuck on `processing`. Inline mode (the default) blocks the request through embedding. | `app/services/ingestion_jobs.py` | Redis + Arq/RQ/Celery worker. |
| 2 | **Retrieval is an O(n) Python cosine scan** — loads every chunk for a bot from Mongo per query. `AtlasVectorStore` is a `NotImplementedError` stub. | `app/services/retrieval.py` | Atlas Vector Search index on `chunks.embedding` + `$vectorSearch` aggregation. |
| 3 | **Rate limiter is process-local** — in-memory dict, lost on restart, not shared across instances (also makes `test_rate_limit_kicks_in_after_threshold` flaky in the full-suite run). Only the widget `/ask` path is limited; the dashboard `/ask` isn't. | `app/services/rate_limit.py` | Redis `INCR` + `EXPIRE`, same signature; apply to dashboard `/ask` too. |
| 4 | **Fake providers silently used when keys absent** — `FakeEmbeddingsProvider` / `FakeLLMProvider`; retrieval quality on fake vectors is meaningless. | `embeddings.py`, `llm.py` | Fail loudly (or a clear dev banner) when a real key is expected. |
| 5 | **`conversations` collection is never written** — model + indexes exist; no chat history, no analytics, no transcript view. | `app/models/conversation.py` | Persist each widget turn; surface transcripts in the dashboard. |
| 6 | **No response streaming** — widget blocks until the full answer returns. | `widget.ts`, `routes/widget.py` | SSE / chunked streaming from the `/ask` endpoints. |
| 7 | **Ingestion sources are thin** — paste-text (capped at 100k chars) or single URL only. No file upload (PDF/DOCX), no crawl/sitemap, no re-chunk on model change. | `routes/documents.py` | File upload + storage; multi-page crawl; sitemap ingest. |
| 8 | **Bot behavior isn't editable** — `system_prompt` and `model_tier` (the Sonnet upgrade tier) are set at model defaults; the dashboard only edits appearance. | `routes/bots.py` (`UpdateAppearanceRequest` comment) | A "Behavior" form: prompt + model tier. |
| 9 | Index creation is skipped when `MONGODB_URI` is unset (so the app boots for local/health-check use). | `app/main.py` lifespan | Fine for dev; note it for deploy. |
| 10 | `dashboard_app` still exposes `/docs` and `/openapi.json` publicly (parent app disables them). Not a hole — endpoints still require auth — but usually closed in prod. | `app/main.py` | Disable when `environment == "production"`. |

---

## Not started (❌)

### Infrastructure & ops
- **CI** — no `.github/`. Nothing runs lint / typecheck / `pytest` / `next build` on push.
- **Deployment config** — no Vercel project config, no Dockerfile / Procfile / server setup for the API, no environment matrix (dev/staging/prod).
- **`infra/` Terraform** — only a stub README. Atlas cluster (backups), Vector Search index, Redis, DB users, network access are all manual today. (`AGENTS.md §3/§4`.) Can be provisioned by hand for v1.
- **Redis** — needed for a durable queue (#1) and shared cache/warm state (`AGENTS.md §4`).
- **Atlas monitoring + alerts** (`AGENTS.md §4`).

### Product / platform
- **Error logging / Sentry** — frontend + backend. Nothing captures exceptions today; you'd be blind in prod.
- **Usage metering** — no token/request counting per bot or per user (needed for any usage visibility or abuse caps, even without billing).
- **Quota / abuse limits** — rate limit is a hardcoded 20/min for everyone; no per-bot monthly cap, no dashboard `/ask` limit.
- **Conversation analytics / dashboard** — depends on shortcut #5.
- **Widget polish** — conversation continuity across reloads, unread indicator, richer a11y, retry on network error.

_Stripe / paid billing: out of scope for this project — not planned._

### Housekeeping
- **No root `README.md`** (only `AGENTS.md` / `CLAUDE.md`).
- `services/api/README.md` "Layout" section is stale — lists `health.py` only, omits most of `app/`.

---

## Suggested next steps (in order)

1. **Add CI** — lint + typecheck + `pytest` + `next build` on PR. Cheap, catches the "untracked imported file" class of break.
2. **Deployment config** — Vercel for the dashboard; a container + `uvicorn`/`gunicorn` for the API (build + bundle `packages/widget/dist/widget.js` into the image, or set `WIDGET_BUNDLE_PATH`). Set `INGEST_INLINE=false` if the host imposes request timeouts. Lock `CORS_ORIGINS` to the real dashboard origin only. Use a Clerk **production** instance.
3. **Error logging / Sentry** — so prod failures are visible.
4. **Redis + real queue** (shortcut #1) — once ingestion reliability or volume needs it; also makes the rate limiter durable (#3).
5. **`infra/` Terraform** for Atlas (cluster + Vector Search index) + Redis, then wire `AtlasVectorStore` (#2).
