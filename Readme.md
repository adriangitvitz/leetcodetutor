# Leetcode Tutor


A two-pane reading room for studying LeetCode problems. The left pane shows
the canonical problem statement; the right pane is a tutor with three modes
(structured walkthrough, Socratic questions, freeform chat) backed by an
LLM provider of your choice (OpenRouter, LM Studio, or MLX). Includes
catalog browsing, per-company analytics, and aggregate statistics across
the source dataset.

The app is split into two services: a Python FastAPI backend (`leetapi/`)
that owns the catalog, problem statements, LLM cache, and provider
adapters; and a Next.js frontend (`web/`) that talks to the backend over
HTTP and renders the UI.

<img width="2520" height="1294" alt="Screenshot 2026-05-02 at 7 09 57 p m" src="https://github.com/user-attachments/assets/e1efb62a-d6ae-4941-beee-db5aa838ec43" />

<img width="2500" height="1155" alt="Screenshot 2026-05-02 at 7 11 03 p m" src="https://github.com/user-attachments/assets/06e3b6ee-07b5-4994-8147-190cd05df123" />

<img width="2527" height="1177" alt="Screenshot 2026-05-02 at 7 10 53 p m" src="https://github.com/user-attachments/assets/d29d73b3-2d6e-4c92-9cf0-3e5d4cbd817d" />


## Requirements

- Python 3.13+ with [uv](https://docs.astral.sh/uv/) on `PATH`
- Node 20+ with `npm`
- An OpenRouter API key, or a running LM Studio / MLX server, for the
  tutor LLM features. Catalog browsing and statistics work without one.

## Run it

1. Clone this repository and move into it.

   ```
   git clone <this-repo-url> leetcode-tutor
   cd leetcode-tutor
   ```

2. Pull the upstream problem dataset into the `problems/` directory. The
   catalog is built from `problems/<Company>/5. All.csv` files contributed
   by the community at
   [liquidslr/interview-company-wise-problems](https://github.com/liquidslr/interview-company-wise-problems).

   ```
   git clone https://github.com/liquidslr/interview-company-wise-problems problems
   ```

3. Install Python and Node dependencies.

   ```
   make install
   ```

4. Configure your LLM provider. Copy the template and fill in your key.

   ```
   cp web/.env.local.example leetapi/.env
   ```

   Edit `leetapi/.env` and set `OPENROUTER_API_KEY` (or switch
   `LLM_PROVIDER` to `lmstudio` / `mlx` and adjust the matching URL).

5. Build the catalog database. Reads every CSV under `problems/`,
   deduplicates per problem, and writes `data/app.db` (a single SQLite
   file managed by Alembic migrations).

   ```
   make ingest
   ```

6. Start both services in parallel.

   ```
   make dev
   ```

   - Frontend: `http://localhost:3000`
   - Backend OpenAPI docs: `http://localhost:4000/docs`

## Common operations

- `make test` runs the FastAPI test suite.
- `make validate-palette` checks both UI palettes against the
  WCAG-AAA-keratoconus contrast band.
- `make import-legacy` performs a one-shot migration of pre-existing
  `data/leetcode/*.md` files and `data/cache.db` into the new schema.
  Idempotent.
- Persona, palette, provider, and model are adjustable from the **Tweaks**
  panel in the topbar. Selections persist in `localStorage`.

## Notes

- The `problems/` directory is treated as external data and is listed in
  `.gitignore`. If you previously had it tracked, run
  `git rm --cached -r problems/` once to detach it, then re-clone the
  upstream repo into the same path.
- `data/` is also gitignored. Re-running `make ingest` rebuilds it from
  scratch and is safe to do at any time.
