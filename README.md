# Askbox

Train a chatbot on your own website or documents, then embed it on any site with a single
`<script>` tag. Askbox is a small SaaS-style project with two surfaces:

1. **Dashboard** — sign in, create a bot, point it at a URL (or paste text), tune its
   look, and copy an embed snippet.
2. **Embeddable widget** — a tiny, dependency-free chat bubble that runs on the customer's
   third-party site and talks to the Askbox API.

"Training" here means **chunk → embed → upsert vectors** (seconds), not model training.
Answers are generated with Claude over retrieved context (RAG). No `.pth` files anywhere.

> Status: this is an in-progress rebuild. Core end-to-end flow works; some pieces are
> deliberate shortcuts. See **[`ROADMAP.md`](ROADMAP.md)** for the honest state of every
> area, and **[`AGENTS.md`](AGENTS.md)** for the target architecture and hard rules.

---

## Architecture

| Concern | Choice |
|---|---|
| Dashboard | Next.js 16 (App Router) · React 19 · TypeScript · Tailwind v4 |
| Dashboard auth | Clerk |
| Backend API | FastAPI (async) · Uvicorn · Pydantic models on every request/response |
| Bot brain | Claude via the Anthropic API — Haiku default, Sonnet on the `model_tier` upgrade |
| Embeddings | Voyage AI (fake fallback when no key) |
| Vector store | MongoDB Atlas — cosine scan today, Atlas Vector Search is the target |
| Primary DB | MongoDB Atlas (`motor`) |
| Widget | Vanilla TS in a Shadow DOM, esbuild IIFE bundle (~4 KB), no runtime deps |
| Widget auth | Public per-bot site key + domain allow-list + per-bot rate limit (no cookies) |

**Data model:** `users` · `bots` · `documents` · `chunks` (vectors) · `conversations`.

### Request flow

```
Dashboard (Clerk session)  ──►  API /bots, /documents, /bots/{id}/ask
                                   │
Customer site <script>  ──►  API /widget/{site_key}/config , /widget/{site_key}/ask
                                   │
                          chunk → embed (Voyage) → store vectors (Mongo)
                          ask  → embed question → top-k chunks → Claude → answer
```

The dashboard's API client attaches the Clerk session token as a bearer token; the API
verifies it against Clerk's JWKS (RS256, stateless) and derives the owner from it. The
widget never sends a token — it authenticates with the public site key, and the API
enforces the bot's domain allow-list per request.

---

## Monorepo layout

```
.
├── apps/
│   └── dashboard/      Next.js dashboard (Clerk, bot CRUD, appearance, embed snippet)
├── services/
│   └── api/            FastAPI backend — ingestion, RAG, widget API, /widget.js
├── packages/
│   └── widget/         Embeddable chat widget bundle
├── infra/              Terraform for MongoDB Atlas etc. (not yet scaffolded)
├── AGENTS.md           Architecture, build order, and hard rules — read first
└── ROADMAP.md          What's done / shortcut / not started
```

---

## Quick start

Each piece runs independently. For the full loop you need the **API** (with a MongoDB
connection) and the **dashboard**; build the **widget** once so the API can serve it.

### 1. API (`services/api/`)

```bash
cd services/api
python -m venv venv
venv\Scripts\activate                # Windows  (source venv/bin/activate elsewhere)
pip install -e ".[dev]"
copy .env.example .env               # then fill in MONGODB_URI, keys, CLERK_JWKS_URL
uvicorn app.main:app --reload --port 8002
```

- Liveness: `GET /health` · Readiness (pings Mongo): `GET /health/ready`
- Interactive docs at `/docs` (disabled when `ENVIRONMENT=production`)
- Without `ANTHROPIC_API_KEY` / `VOYAGE_API_KEY` the API falls back to fake LLM/embeddings
  so you can develop offline; in `production` it refuses to start without them.

### 2. Widget (`packages/widget/`)

```bash
cd packages/widget
npm install
npm run build            # -> dist/widget.js, which the API serves at GET /widget.js
npm run dev              # rebuild on change
```

### 3. Dashboard (`apps/dashboard/`)

```bash
cd apps/dashboard
npm install
# .env.local: NEXT_PUBLIC_CLERK_* + CLERK_SECRET_KEY, API_BASE_URL=http://127.0.0.1:8002
npm run dev              # http://localhost:3000
```

---

## Configuration

All config is environment variables — no URLs, keys, or connection strings in code.
`.env` / `.env.local` files are git-ignored and local only.

**API** (`services/api/.env`, see `.env.example` for the full list)

| Var | Purpose |
|---|---|
| `MONGODB_URI` | Atlas connection string |
| `ANTHROPIC_API_KEY` | Claude; omit for a fake LLM in dev |
| `VOYAGE_API_KEY` | Embeddings; omit for fake embeddings in dev |
| `CLERK_JWKS_URL` | Verifies dashboard session tokens |
| `ENVIRONMENT` | `production` hardens startup and hides `/docs` |
| `INGEST_INLINE` | `false` runs ingestion as a background task instead of blocking the request |
| `WIDGET_BUNDLE_PATH` | Where `GET /widget.js` reads the built bundle from |

**Dashboard** (`apps/dashboard/.env.local`)

| Var | Purpose |
|---|---|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY` | Clerk |
| `API_BASE_URL` | Internal API base (not `NEXT_PUBLIC_` — server-only) |
| `WIDGET_SCRIPT_URL` | Overrides the embed snippet's script src (defaults to `${API_BASE_URL}/widget.js`) |

---

## Testing

```bash
cd services/api && pytest
```

`pytest` + `pytest-asyncio`, ~90 tests covering auth, bots, documents, the widget API,
ingestion, RAG, web-fetch/SSRF guard, domains, and models. Several suites hit a live Atlas
cluster (`MONGODB_URI` from `.env`) and take a few minutes.

Dashboard: `npm run lint` and `npx tsc --noEmit` in `apps/dashboard/`.
Widget: `npm run typecheck` in `packages/widget/`.

---

## Security notes

- **Never commit secrets.** Config is env-only; `.env*` is git-ignored.
- Every bot-scoped API endpoint verifies the bot belongs to the authenticated user.
- The widget runs on third-party origins: public site key + per-bot domain allow-list
  (exact host + subdomain match), checked server-side, plus a per-bot rate limit.
- URL ingestion has an SSRF guard: public hosts only, redirect re-validation per hop,
  size and content-type caps.
