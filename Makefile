PY := .venv/bin/python

.PHONY: local dev api web build install test discover tailor base-resumes outreach-linkedin tidy

# Daily use: serve the committed React build + API on localhost:8000, reading the
# live DB from .env (Turso if set, else local SQLite).
local:
	$(PY) -m uvicorn api.main:app --port 8000

# Dev: API with hot-reload + Vite dev server (Ctrl-C stops both)
dev:
	$(PY) -m uvicorn api.main:app --reload --port 8000 & npm run dev; kill %1

api:
	$(PY) -m uvicorn api.main:app --reload --port 8000

web:
	npm run dev

# Rebuild React → apps/web/dist (served by `make local`)
build:
	npm run build

install:
	$(PY) -m pip install -r requirements.txt
	$(PY) -m pip install -e .
	npm run install:web

test:
	$(PY) -m pytest -q

# Scrape + filter all enabled sources now (GitHub Actions also does this daily)
discover:
	$(PY) main.py

# Tailor the top N new jobs with the Claude CLI (Haiku). N=5 by default.
tailor:
	$(PY) main.py --tailor --limit $(or $(N),5)

# Render the 4 untailored track resumes → output/resumes/base/
base-resumes:
	$(PY) main.py --base-resumes

# Rank LinkedIn connections into a referral worklist (reads data/linkedin/Connections.csv).
# ARGS examples: ARGS="--load", ARGS="--top 60 --load".
outreach-linkedin:
	$(PY) scripts/linkedin_outreach.py $(ARGS)

# Delete un-applied listings (new/queued) older than 30 days. ARGS="--dry-run", "--days N".
tidy:
	$(PY) scripts/cleanup_stale_jobs.py $(ARGS)
