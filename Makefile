.PHONY: dev api web install build prod local outreach-linkedin sync-turso tidy

# Dev: open two cmd windows (Windows) running both servers
dev:
	@echo "Starting FastAPI (8000) + Vite (3000)..."
	@start cmd /k "uvicorn api.main:app --reload --port 8000"
	@start cmd /k "npm run dev"

# Run only the FastAPI backend (dev, with hot-reload)
api:
	uvicorn api.main:app --reload --port 8000

# Run only the React dev server (delegates to apps/web via root package.json)
web:
	npm run dev

# Build React for production (output to apps/web/dist, served by FastAPI)
build:
	npm run build

# Production: build React then serve everything from FastAPI
prod: build
	uvicorn api.main:app --host 0.0.0.0 --port 8000

# Local-only (the way this project runs): serve the committed build + API on
# localhost, reading the live DB from .env (Turso if set, else local SQLite).
# No rebuild. GitHub Actions keeps the data fresh; `git pull` grabs new PDFs.
local:
	uvicorn api.main:app --port 8000

# Rank LinkedIn connections into a referral worklist with per-contact DM drafts
# (reads the gitignored data/linkedin/Connections.csv; writes output/outreach/).
# ARGS examples: ARGS="--load" (upsert into recruiters), ARGS="--top 60 --load".
outreach-linkedin:
	python scripts/linkedin_outreach.py $(ARGS)

# Push local personal state (tracked jobs, recruiters, outreach) up to Turso so
# the cloud daily reminder sees it. Needs TURSO_* in .env. ARGS="--dry-run" to
# preview.
sync-turso:
	python scripts/sync_to_turso.py $(ARGS)

# Delete un-applied listings (new/queued) older than 30 days. Targets Turso when
# TURSO_* is in .env, else the local DB. ARGS="--dry-run" to preview, "--days N".
tidy:
	python scripts/cleanup_stale_jobs.py $(ARGS)

# Install all dependencies (Python + Node)
install:
	pip install -r requirements.txt
	pip install -e .
	npm run install:web
