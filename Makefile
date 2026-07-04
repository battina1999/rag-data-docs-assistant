.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help setup ingest serve ask eval test docker-up docker-down clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Install dependencies
	pip install -r requirements.txt

ingest: ## Build the FAISS index + SQLite catalog from knowledge_base/
	python -m app.ingest

serve: ## Run the FastAPI app (http://localhost:8000, docs at /docs)
	uvicorn app.api:app --reload --port 8000

ask: ## Ask a question from the CLI:  make ask q="What is the grain of fact_flights?"
	python scripts/ask.py "$(q)"

eval: ## Run the evaluation harness (answer/refusal/retrieval metrics)
	python -m eval.evaluate

test: ## Run the test suite (self-contained, no API key needed)
	python -m pytest -q

docker-up: ## Build + run the assistant via Docker (port 8000)
	docker compose up --build

docker-down: ## Stop the container
	docker compose down

clean: ## Remove the built index
	rm -rf index
