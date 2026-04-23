.DEFAULT_GOAL := help
PY ?= python3.12
PKG := xtv_support

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: install
install: ## Create venv + install dev extras
	$(PY) -m venv .venv
	. .venv/bin/activate && pip install -U pip && pip install -e '.[dev]'

.PHONY: install-all
install-all: ## Install every optional dependency group
	. .venv/bin/activate && pip install -e '.[all]'

.PHONY: dev
dev: ## Run the bot locally
	. .venv/bin/activate && python main.py

.PHONY: lint
lint: ## Ruff + mypy
	. .venv/bin/activate && ruff check . && ruff format --check . && mypy src/$(PKG) || mypy app

.PHONY: fmt
fmt: ## Auto-format with ruff
	. .venv/bin/activate && ruff format . && ruff check --fix .

.PHONY: test
test: ## Run the full pytest suite
	. .venv/bin/activate && pytest

.PHONY: cov
cov: ## Run pytest with coverage report
	. .venv/bin/activate && pytest --cov=src/$(PKG) --cov-report=term-missing --cov-report=html

.PHONY: docs-serve
docs-serve: ## Serve MkDocs locally (Phase 15)
	. .venv/bin/activate && mkdocs serve

.PHONY: docs-build
docs-build: ## Build MkDocs static site
	. .venv/bin/activate && mkdocs build --strict

.PHONY: docker-build
docker-build: ## Build the production Docker image
	docker build -f deploy/docker/Dockerfile -t xtv-support:dev .

.PHONY: docker-run
docker-run: ## Run the locally-built image with ./.env
	docker run --rm --env-file .env xtv-support:dev

.PHONY: compose-up
compose-up: ## docker compose up (bot + mongo + redis)
	docker compose -f deploy/compose/docker-compose.yml up

.PHONY: release
release: ## Create & push a signed tag (usage: make release V=0.9.0)
	@if [ -z "$(V)" ]; then echo "V is required, e.g. make release V=0.9.0"; exit 1; fi
	git tag -a v$(V) -m "v$(V)"
	git push origin HEAD --tags

.PHONY: clean
clean: ## Remove caches, build artefacts, coverage
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml docs/site
	find . -type d -name __pycache__ -exec rm -rf {} +
