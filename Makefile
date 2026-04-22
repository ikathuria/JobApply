.PHONY: dev api web install build prod

# Dev: open two cmd windows (Windows) running both servers
dev:
	@echo "Starting FastAPI (8000) + Vite (3000)..."
	@start cmd /k "uvicorn api.main:app --reload --port 8000"
	@start cmd /k "cd web && npm run dev"

# Run only the FastAPI backend (dev, with hot-reload)
api:
	uvicorn api.main:app --reload --port 8000

# Run only the React dev server
web:
	cd web && npm run dev

# Build React for production (output to web/dist, served by FastAPI)
build:
	cd web && npm run build

# Production: build React then serve everything from FastAPI
prod: build
	uvicorn api.main:app --host 0.0.0.0 --port 8000

# Install all dependencies (Python + Node)
install:
	pip install -r requirements.txt
	cd web && npm install
