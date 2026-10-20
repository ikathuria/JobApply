.PHONY: local dev api web build install test discover tailor base-resumes outreach-linkedin tidy

# Daily use: serve the committed React build + API on localhost:8000, reading the
# live DB from .env (Turso if set, else local SQLite).
local:
	uvicorn api.main:app --port 8000

# Dev: API with hot-reload + Vite dev server (Ctrl-C stops both)
dev:
	uvicorn api.main:app --reload --port 8000 & npm run dev; kill %1

api:
	uvicorn api.main:app --reload --port 8000

web:
	npm run dev

# Rebuild React → apps/web/dist (served by `make local`)
build:
	npm run build

install:
	pip install -r requirements.txt
	pip install -e .
	npm run install:web

test:
	python -m pytest -q

# Scrape + filter all enabled sources now (GitHub Actions also does this daily)
discover:
	python main.py

# Tailor the top N new jobs with the Claude CLI (Haiku). N=5 by default.
tailor:
	python main.py --tailor --limit $(or $(N),5)

# Render the 4 untailored track resumes → output/resumes/base/
base-resumes:
	python main.py --base-resumes

# Rank LinkedIn connections into a referral worklist (reads data/linkedin/Connections.csv).
# ARGS examples: ARGS="--load", ARGS="--top 60 --load".
outreach-linkedin:
	python scripts/linkedin_outreach.py $(ARGS)

# Delete un-applied listings (new/queued) older than 30 days. ARGS="--dry-run", "--days N".
tidy:
	python scripts/cleanup_stale_jobs.py $(ARGS)
