.PHONY: install migrate ingest import-legacy api-dev web-dev dev test validate-palette help

help:
	@echo "Targets:"
	@echo "  install            install Python + Node deps"
	@echo "  migrate            alembic upgrade head (creates data/app.db)"
	@echo "  ingest             read problems/*/5. All.csv into the catalog"
	@echo "  import-legacy      migrate old data/leetcode/*.md + cache.db (one-shot)"
	@echo "  api-dev            run leetapi on :4000"
	@echo "  web-dev            run Next.js on :3000"
	@echo "  dev                api-dev + web-dev in parallel"
	@echo "  test               run leetapi pytest suite"
	@echo "  validate-palette   check both web palettes against WCAG-AAA-keratoconus"

# ---- Setup -----------------------------------------------------------------

install:
	cd leetapi && uv sync
	cd web && npm install

migrate:
	cd leetapi && uv run alembic upgrade head

ingest: migrate
	cd leetapi && uv run leetapi ingest

import-legacy:
	cd leetapi && uv run leetapi import-legacy

# ---- Run -------------------------------------------------------------------

api-dev:
	cd leetapi && uv run leetapi serve

web-dev:
	cd web && npm run dev

dev:
	$(MAKE) -j2 api-dev web-dev

# ---- Test ------------------------------------------------------------------

test:
	cd leetapi && uv run pytest

# ---- Palette validation ----------------------------------------------------

validate-palette:
	cd /Users/adriannajera/Projects/misc/colorsenv && python3 validate_lct_palette.py
