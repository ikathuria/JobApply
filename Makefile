.PHONY: dev api web install build

# Run both servers concurrently (requires 'concurrently' or just use two terminals)
dev:
	@echo "Starting FastAPI + Vite dev servers..."
	@start cmd /k "uvicorn api.main:app --reload --port 8000"
	@start cmd /k "cd web && npm run dev"

# Run only the FastAPI backend
api:
	uvicorn api.main:app --reload --port 8000

# Run only the React dev server
web:
	cd web && npm run dev

# Build React for production (output to web/dist, served by FastAPI)
build:
	cd web && npm run build

# Install all dependencies
install:
	pip install -r requirements.txt
	cd web && npm install
