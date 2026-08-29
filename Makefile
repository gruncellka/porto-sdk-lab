.PHONY: . help setup setup-repos setup-all status health check-packages check-gitignore validate lint lint-py lint-ts test test-all test-packages-py test-packages-ts test-packages-bdd test-scripts matrix-orders-sync matrix-orders-sync-check matrix-sdk-sync matrix-sdk-sync-check matrix-sync matrix-sync-check parity-report parity-report-check check-paid-ci-safety promote-evidence surface surface-check surface-structure sm-sync sm-sync-safe sm-sync-remote sm-sync-remote-safe sm-reset-danger install-hooks lab registry labs-verify labs-up labs-up-py labs-up-ts labs-down labs-setup labs-setup-py labs-setup-ts labs-shell-py labs-shell-ts labs-run-py labs-run-ts labs-watch-py labs-watch-ts labs-observe-py labs-observe-ts labs-internetmarke-preflight labs-internetmarke-gate-check labs-internetmarke-post-approval labs-internetmarke-canary labs-internetmarke-full labs-internetmarke-calibration-matrix labs-internetmarke-measure labs-internetmarke-calibration labs-internetmarke-py labs-internetmarke-ts labs-clean clean clean-py clean-ts clean-sdks clean-deps clean-repos clean-all clean-nuclear

# Plain `make`
.DEFAULT_GOAL := .

# Python interpreter used to bootstrap the workspace venv and run helper
# scripts. We deliberately prefer an explicit `python3.13` (matching
# `requires-python` in pyproject.toml) so that `make` recipes — which run
# under /bin/sh and ignore shell aliases / interactive PATH tweaks — do not
# accidentally pick up the system Python (3.9 on macOS).
# Override with: `make PYTHON=/path/to/python3.13`.
PYTHON ?= $(shell command -v python3.13 2>/dev/null || command -v python3)

# Helper functions to check prerequisites
check-packages:
	@if [ ! -d "sdks/porto-sdk-python" ] || [ ! -d "sdks/porto-sdk-typescript" ]; then \
		echo "❌ Error: SDKs not found. Run 'make' first."; \
		echo ""; \
		echo "   Required SDKs:"; \
		echo "   - sdks/porto-sdk-python"; \
		echo "   - sdks/porto-sdk-typescript"; \
		echo ""; \
		echo "   Run: make setup-repos"; \
		exit 1; \
	fi
	@if [ ! -f "sdks/porto-sdk-python/pyproject.toml" ]; then \
		echo "❌ Error: Python SDK not properly cloned. Run 'make setup-repos' first."; \
		exit 1; \
	fi
	@if [ ! -f "sdks/porto-sdk-typescript/package.json" ]; then \
		echo "❌ Error: TypeScript SDK not properly cloned. Run 'make setup-repos' first."; \
		exit 1; \
	fi

help: ## Show available commands grouped by action
	@echo "Porto SDK Lab - Available commands:"
	@echo ""
	@echo "📦 Setup:"
	@echo "  \033[36mmake\033[0m                      Bootstrap venv + pre-commit hooks (default)"
	@grep -E '^setup[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🔄 Submodules:"
	@grep -E '^sm-[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "📋 Matrix:"
	@grep -E '^matrix-[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@grep -E '^(parity-report|check-paid-ci-safety|promote-evidence):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "✅ Validate:"
	@grep -E '^(validate|check-gitignore):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🩺 Health:"
	@grep -E '^(status|health):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🔍 Linting:"
	@grep -E '^lint[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🧪 Testing:"
	@grep -E '^test[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🐳 Labs (Docker):"
	@grep -E '^labs-[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "📐 Surface:"
	@grep -E '^surface[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🧹 Cleanup:"
	@grep -E '^clean[a-zA-Z_-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "📋 Quick Start:"
	@echo "  1. make                  - Bootstrap venv + pre-commit hooks"
	@echo "  2. make help             - Show all commands"
	@echo "  3. make labs-up          - Start lab containers"
	@echo "  4. make labs-setup       - Setup lab environments in Docker"
	@echo "  5. make validate        - Full required health checks"
	@echo "  6. make lint            - Pre-commit hygiene only"

# ============================================================================
# Setup
# ============================================================================
.: ## Bootstrap venv + pre-commit hooks (default — same as plain `make`)
	@$(PYTHON) scripts/setup.py

setup: . ## Alias for default `make` (backward compatible)

setup-repos: ## Clone SDKs and resources from .gitmodules only
	@$(PYTHON) scripts/setup.py --repos-only

setup-all: ## Complete workspace setup (repos + environment)
	@$(PYTHON) scripts/setup.py --all

status: ## Show workspace status (venv, submodules, SDKs, resources)
	@$(PYTHON) scripts/status.py

health: ## Workspace health (submodules + status)
	@$(MAKE) setup-repos
	@$(MAKE) sm-sync
	@$(MAKE) status

lab: check-packages ## Overlay Lab resource checkouts into both SDK installs
	@chmod +x scripts/lab/overlay-python.sh scripts/lab/restore-python.sh
	@scripts/lab/overlay-python.sh "$(CURDIR)/sdks/porto-sdk-python"
	@node scripts/lab/link-typescript.mjs "$(CURDIR)/sdks/porto-sdk-typescript"

registry: check-packages ## Restore registry porto-data / porto-features in both SDKs
	@chmod +x scripts/lab/overlay-python.sh scripts/lab/restore-python.sh
	@scripts/lab/restore-python.sh "$(CURDIR)/sdks/porto-sdk-python"
	@node scripts/lab/unlink-typescript.mjs "$(CURDIR)/sdks/porto-sdk-typescript"
	@$(MAKE) labs-verify

# ============================================================================
# Labs (Docker-first)
# ============================================================================
labs-verify: ## Verify Docker lab mounts and runtime paths
	@./scripts/labs/verify.sh

labs-up: ## Start both Docker lab containers
	@./scripts/labs/up.sh

labs-up-py: ## Start Python lab container only
	@LABS=py ./scripts/labs/up.sh

labs-up-ts: ## Start TypeScript lab container only
	@LABS=ts ./scripts/labs/up.sh

labs-down: ## Stop Docker lab containers
	@./scripts/labs/down.sh

labs-setup: sm-sync check-packages ## Setup all labs inside Docker containers (after syncing pinned submodule SHAs)
	@bash ./scripts/labs/setup/all.sh

labs-setup-py: sm-sync check-packages ## Setup Python lab inside Docker (after syncing pinned submodule SHAs)
	@bash ./scripts/labs/setup/py.sh

labs-setup-ts: sm-sync check-packages ## Setup TypeScript lab inside Docker (after syncing pinned submodule SHAs)
	@bash ./scripts/labs/setup/ts.sh

labs-shell-py: ## Open interactive shell in Python lab container
	@bash ./scripts/labs/shell/py.sh

labs-shell-ts: ## Open interactive shell in TypeScript lab container
	@bash ./scripts/labs/shell/ts.sh

labs-run-py: ## Run Python lab script (usage: make labs-run-py SCRIPT=example_fastapi_integration.py)
	@bash ./scripts/labs/run/py.sh $(or $(SCRIPT),example_fastapi_integration.py)

labs-run-ts: ## Run TypeScript lab script (usage: make labs-run-ts SCRIPT=example_nextjs_integration.ts)
	@bash ./scripts/labs/run/ts.sh $(or $(SCRIPT),example_nextjs_integration.ts)

labs-watch-py: ## Watch and rerun Python lab script (usage: make labs-watch-py SCRIPT=example_fastapi_integration.py)
	@bash ./scripts/labs/watch/py.sh $(or $(SCRIPT),example_fastapi_integration.py)

labs-watch-ts: ## Watch and rerun TypeScript lab script (usage: make labs-watch-ts SCRIPT=example_nextjs_integration.ts)
	@bash ./scripts/labs/watch/ts.sh $(or $(SCRIPT),example_nextjs_integration.ts)

labs-observe-py: ## Run Python lab script with external observer experiments
	@bash ./scripts/labs/observers/py.sh $(or $(SCRIPT),example_basic.py)

labs-observe-ts: ## Run TypeScript lab script with external observer experiments
	@bash ./scripts/labs/observers/ts.sh $(or $(SCRIPT),example_basic.ts)

labs-internetmarke-preflight: ## Internetmarke preflight — API + auth, no purchase (safe while waiting for DHL approval)
	@bash ./scripts/labs/run/py.sh example_internetmarke_preflight.py

labs-internetmarke-gate-check: ## Two approval gates only — DHL app + Portokasse user (no purchase)
	@bash ./scripts/labs/run/py.sh example_internetmarke_gate_check.py

labs-internetmarke-post-approval: ## After DHL approves app: gate check then canary purchase if ready
	@bash ./scripts/labs/internetmarke-post-approval.sh

labs-internetmarke-py: ## Manual Internetmarke matrix (Python) — costs money; PROFILE=canary|full|dry_run
	@PORTO_LAB_HTTP_TRACE=1 PORTO_LAB_HTTP_TRACE_BODIES=1 PROFILE=$(or $(PROFILE),canary) $(PYTHON) ./scripts/labs/observers/runner.py \
	  --label "internetmarke-py:$(or $(PROFILE),canary)" -- \
	  bash ./scripts/labs/run/experiment-py.sh labs/experiments/internetmarke/order_matrix.py

labs-internetmarke-ts: ## Manual Internetmarke matrix (TypeScript) — costs money; PROFILE=canary|full|dry_run
	@PORTO_LAB_HTTP_TRACE=1 PORTO_LAB_HTTP_TRACE_BODIES=1 PROFILE=$(or $(PROFILE),canary) $(PYTHON) ./scripts/labs/observers/runner.py \
	  --label "internetmarke-ts:$(or $(PROFILE),canary)" -- \
	  bash ./scripts/labs/run/experiment-ts.sh labs/experiments/internetmarke/order_matrix.ts

labs-internetmarke-canary: ## Manual canary purchase (Py then TS, 1 case each)
	@$(MAKE) labs-internetmarke-py PROFILE=canary
	@$(MAKE) labs-internetmarke-ts PROFILE=canary

labs-internetmarke-full: ## Manual full matrix (Py then TS) — costs money
	@$(MAKE) labs-internetmarke-py PROFILE=full
	@$(MAKE) labs-internetmarke-ts PROFILE=full

labs-internetmarke-calibration-matrix: ## Paid: ADDRESS_ZONE full + FRANKING_ZONE franking_full (92 cases, ~€602)
	@$(MAKE) labs-internetmarke-py PROFILE=full
	@$(MAKE) labs-internetmarke-py PROFILE=franking_full

labs-internetmarke-measure: ## Measure calibration runs (ADDRESS + FRANKING) vs porto-data
	@bash ./scripts/labs/measure-internetmarke-calibration.sh

labs-internetmarke-calibration: ## Paid calibration matrix then measure both runs
	@$(MAKE) labs-internetmarke-calibration-matrix
	@$(MAKE) labs-internetmarke-measure

labs-clean: ## Remove Docker lab containers and volumes
	@./scripts/labs/clean.sh

# ============================================================================
# Surface (internal drift/parity + full structure)
# ============================================================================
.PHONY: surface surface-structure

surface: ## Generate public-surface artifacts (python.json / typescript.json / report.json) for both SDKs
	@if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; \
	elif [ -x "venv/bin/python" ]; then PY="venv/bin/python"; \
	else echo "Error: Workspace venv not found. Run 'make' first."; exit 1; fi; \
	PYTHONPATH=. $$PY surface/generate.py

surface-check: ## Verify public-surface parity (exit non-zero on report errors)
	@if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; \
	elif [ -x "venv/bin/python" ]; then PY="venv/bin/python"; \
	else echo "Error: Workspace venv not found. Run 'make' first."; exit 1; fi; \
	PYTHONPATH=. $$PY surface/generate.py --check --no-markdown

surface-structure: ## Generate full SDK structure stubs (declarations only) for both SDKs
	@if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; \
	elif [ -x "venv/bin/python" ]; then PY="venv/bin/python"; \
	else echo "❌ Error: Workspace venv not found. Run 'make' first."; exit 1; fi; \
	PYTHONPATH=. $$PY surface/generate_structure.py

# ============================================================================
# Submodules (explicit sm-* command set)
# ============================================================================
sm-sync: ## Reset all submodules to Lab-pinned commits after pull (git submodule update --init --recursive)
	@$(PYTHON) scripts/sync.py $(if $(AUTOSTASH),--autostash,)

sm-sync-remote: ## Move submodules to latest remote default branch (git submodule update --remote --init --recursive)
	@$(PYTHON) scripts/sync.py --remote $(if $(AUTOSTASH),--autostash,)

sm-reset-danger: ## DESTRUCTIVE: Hard-reset resources/porto-data and resources/porto-features to origin/main (drop all local changes)
	@echo "⚠️  DESTRUCTIVE ACTION"
	@echo "   This will permanently remove local commits/changes in:"
	@echo "   - resources/porto-data"
	@echo "   - resources/porto-features"
	@echo "   and force both to match origin/main."
	@read -p "   Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "🔁 Syncing submodule URLs from .gitmodules..."; \
		git submodule sync -- "resources/porto-data" "resources/porto-features"; \
		echo "📥 Resetting resources/porto-data to origin/main..."; \
		git -C resources/porto-data fetch origin main; \
		git -C resources/porto-data reset --hard origin/main; \
		git -C resources/porto-data clean -fd; \
		echo "📥 Resetting resources/porto-features to origin/main..."; \
		git -C resources/porto-features fetch origin main; \
		git -C resources/porto-features reset --hard origin/main; \
		git -C resources/porto-features clean -fd; \
		echo "✅ Resources reset complete."; \
		echo "ℹ️  Parent repo may now show modified submodule pointers."; \
	else \
		echo "❌ Cancelled"; \
		exit 1; \
	fi

# Safety wrappers
sm-sync-safe: ## sm-sync with autostash enabled
	@$(MAKE) sm-sync AUTOSTASH=1
sm-sync-remote-safe: ## sm-sync-remote with autostash enabled
	@$(MAKE) sm-sync-remote AUTOSTASH=1

matrix-orders-sync: ## Regenerate Lab matrix/orders.generated.yaml from porto-data wire
	@if [ ! -x "venv/bin/python" ]; then \
		echo "❌ Error: Workspace venv not found. Run 'make' first."; \
		exit 1; \
	fi
	@venv/bin/python scripts/matrix-orders-sync.py

matrix-orders-sync-check: ## Verify Lab matrix/orders.generated.yaml matches porto-data (CI)
	@if [ ! -x "venv/bin/python" ]; then \
		echo "❌ Error: Workspace venv not found. Run 'make' first."; \
		exit 1; \
	fi
	@venv/bin/python scripts/matrix-orders-sync.py --check

matrix-sdk-sync: ## Regenerate Lab matrix/sdk.yaml from @sdk Gherkin
	@if [ ! -x "venv/bin/python" ]; then \
		echo "❌ Error: Workspace venv not found. Run 'make' first."; \
		exit 1; \
	fi
	@venv/bin/python scripts/matrix-sdk-sync.py

matrix-sdk-sync-check: ## Verify sdk.yaml matches @sdk scenarios (CI)
	@if [ ! -x "venv/bin/python" ]; then \
		echo "❌ Error: Workspace venv not found. Run 'make' first."; \
		exit 1; \
	fi
	@venv/bin/python scripts/matrix-sdk-sync.py --check

matrix-sync: matrix-sdk-sync matrix-orders-sync ## Regenerate sdk.yaml and orders.generated.yaml

matrix-sync-check: matrix-sdk-sync-check matrix-orders-sync-check ## Verify all matrix artifacts (CI)

parity-report: ## Generate docs/sdks/parity.md (@sdk step parity)
	@if [ ! -x "venv/bin/python" ]; then \
		echo "❌ Error: Workspace venv not found. Run 'make' first."; \
		exit 1; \
	fi
	@venv/bin/python scripts/parity-report.py

parity-report-check: ## Verify parity.md and @sdk step parity (CI)
	@if [ ! -x "venv/bin/python" ]; then \
		echo "❌ Error: Workspace venv not found. Run 'make' first."; \
		exit 1; \
	fi
	@venv/bin/python scripts/parity-report.py --check

check-paid-ci-safety: ## Fail if standard CI workflows reference paid patterns
	@sh scripts/check-paid-ci-safety.sh

promote-evidence: ## Promote green lab run cases into orders.generated.yaml (usage: RUN_ID=...)
	@if [ ! -x "venv/bin/python" ]; then \
		echo "❌ Error: Workspace venv not found. Run 'make' first."; \
		exit 1; \
	fi
	@if [ -z "$(RUN_ID)" ]; then \
		echo "❌ Usage: make promote-evidence RUN_ID=<labs/experiments/runs/id>"; \
		exit 1; \
	fi
	@venv/bin/python scripts/labs/promote-evidence.py $(RUN_ID) $(if $(DRY_RUN),--dry-run,)

# ============================================================================
# Validation (pre-commit / CI leaves / validate)
# ============================================================================
check-gitignore: ## Fail if generated paths are tracked in git
	@if [ ! -x "venv/bin/python" ]; then \
		echo "Error: Workspace venv not found. Run 'make' first."; \
		exit 1; \
	fi
	@venv/bin/python scripts/check_gitignore.py

validate: check-gitignore lint lint-py lint-ts test-scripts matrix-sync-check check-paid-ci-safety surface-check ## Required repository health (all leaf checks)

# ============================================================================
# Linting
# ============================================================================
lint: ## Run pre-commit on all files (cheap local hygiene)
	@if [ ! -d "venv" ]; then \
		echo "Error: Workspace venv not found. Run 'make' first."; \
		exit 1; \
	fi
	@. venv/bin/activate && SKIP=guard-submodule-pointer-commit pre-commit run --all-files

lint-py: ## Run pre-commit on Python lab only
	@if [ ! -d "venv" ]; then \
		echo "❌ Error: Workspace venv not found. Run 'make' first."; \
		exit 1; \
	fi
	@. venv/bin/activate && pre-commit run --config .pre-commit-config-py-lab.yaml --all-files

lint-ts: ## Run pre-commit on TypeScript lab only
	@if [ ! -d "venv" ]; then \
		echo "❌ Error: Workspace venv not found. Run 'make' first."; \
		exit 1; \
	fi
	@. venv/bin/activate && pre-commit run --config .pre-commit-config-ts-lab.yaml --all-files

# ============================================================================
# Install
# ============================================================================
install-hooks: ## Install pre-commit hooks - requires: make
	@if [ ! -d "venv" ]; then \
		echo "❌ Error: Workspace venv not found. Run 'make' first."; \
		exit 1; \
	fi
	@if [ ! -f "venv/bin/pre-commit" ]; then \
		echo "❌ Error: pre-commit not installed. Run 'make' first."; \
		exit 1; \
	fi
	@venv/bin/pre-commit install
	@echo "✓ Pre-commit hooks installed"

# ============================================================================
# Testing
# ============================================================================
test: test-all ## Alias for test-all

test-all: check-packages ## Run unit + @sdk BDD for both SDKs - requires: make
	@echo "🧪 Running unpaid tests..."
	@if [ -d "sdks/porto-sdk-python/.venv" ] || [ -d "sdks/porto-sdk-python/venv" ]; then \
		cd sdks/porto-sdk-python && $(MAKE) test && $(MAKE) sdk; \
	else \
		echo "⚠️  Python SDK venv not found. Run: cd sdks/porto-sdk-python && make"; \
	fi
	@if [ -d "sdks/porto-sdk-typescript/node_modules" ]; then \
		cd sdks/porto-sdk-typescript && $(MAKE) test && $(MAKE) sdk; \
	elif [ -f "sdks/porto-sdk-typescript/package.json" ]; then \
		echo "⚠️  TypeScript SDK not installed. Run: cd sdks/porto-sdk-typescript && make"; \
	else \
		echo "⚠️  TypeScript SDK not found. Skipping TypeScript tests."; \
	fi

test-packages-py: check-packages ## Run Python SDK unpaid tests - requires: make
	@cd sdks/porto-sdk-python && $(MAKE) test

test-packages-ts: check-packages ## Run TypeScript SDK unpaid tests - requires: make
	@cd sdks/porto-sdk-typescript && $(MAKE) test

test-packages-bdd: check-packages ## Run @sdk BDD for both SDKs - requires: make
	@if [ -d "sdks/porto-sdk-python/.venv" ] || [ -d "sdks/porto-sdk-python/venv" ]; then \
		cd sdks/porto-sdk-python && $(MAKE) sdk; \
	else \
		echo "Python SDK venv not found. Run: cd sdks/porto-sdk-python && make"; \
	fi
	@if [ -d "sdks/porto-sdk-typescript/node_modules" ]; then \
		cd sdks/porto-sdk-typescript && $(MAKE) sdk; \
	elif [ -f "sdks/porto-sdk-typescript/package.json" ]; then \
		echo "TypeScript SDK not installed. Run: cd sdks/porto-sdk-typescript && make"; \
	else \
		echo "TypeScript SDK not found. Skipping TypeScript BDD tests."; \
	fi

test-scripts: ## Run Lab workspace pytest (scripts + surface)
	@if [ ! -d "venv" ]; then \
		echo "❌ Error: Workspace venv not found. Run 'make' first."; \
		exit 1; \
	fi
	@echo "🧪 Running script tests..."
	@. venv/bin/activate && pytest -v

# ============================================================================
# Cleanup
# ============================================================================
clean: ## Clean build artifacts and caches (keeps dependencies)
	@echo "🧹 Cleaning workspace artifacts..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".coverage.*" -delete 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.tsbuildinfo" -delete 2>/dev/null || true
	@find . -type d -name ".turbo" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@echo "🧹 Cleaning SDK packages..."
	@if [ -d "sdks/porto-sdk-python" ] && [ -f "sdks/porto-sdk-python/Makefile" ]; then \
		cd sdks/porto-sdk-python && $(MAKE) clean; \
	fi
	@if [ -d "sdks/porto-sdk-typescript" ] && [ -f "sdks/porto-sdk-typescript/Makefile" ]; then \
		cd sdks/porto-sdk-typescript && $(MAKE) clean; \
	fi
	@echo "✅ Build artifacts cleaned"

clean-py: ## Clean Python-specific artifacts
	@echo "🧹 Cleaning Python artifacts..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@if [ -d "sdks/porto-sdk-python" ] && [ -f "sdks/porto-sdk-python/Makefile" ]; then \
		cd sdks/porto-sdk-python && $(MAKE) clean; \
	fi
	@echo "✅ Python artifacts cleaned"

clean-ts: ## Clean TypeScript-specific artifacts
	@echo "🧹 Cleaning TypeScript artifacts..."
	@find . -type d -name "dist" -path "*/sdks/*" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.tsbuildinfo" -delete 2>/dev/null || true
	@find . -type d -name ".turbo" -exec rm -rf {} + 2>/dev/null || true
	@if [ -d "sdks/porto-sdk-typescript" ] && [ -f "sdks/porto-sdk-typescript/Makefile" ]; then \
		cd sdks/porto-sdk-typescript && $(MAKE) clean; \
	fi
	@echo "✅ TypeScript artifacts cleaned"

clean-sdks: ## Clean SDK packages only (artifacts and dependencies)
	@echo "🧹 Cleaning SDK packages..."
	@if [ -d "sdks/porto-sdk-python" ] && [ -f "sdks/porto-sdk-python/Makefile" ]; then \
		cd sdks/porto-sdk-python && $(MAKE) clean-all; \
	fi
	@if [ -d "sdks/porto-sdk-typescript" ] && [ -f "sdks/porto-sdk-typescript/Makefile" ]; then \
		cd sdks/porto-sdk-typescript && $(MAKE) clean-all; \
	fi
	@echo "✅ SDK packages cleaned"

clean-deps: ## Clean installed dependencies (venv, node_modules)
	@echo "🧹 Cleaning dependencies..."
	@echo "  → Removing workspace venv..."
	@rm -rf venv 2>/dev/null || true
	@echo "  → Cleaning SDK package dependencies..."
	@if [ -d "sdks/porto-sdk-python" ] && [ -f "sdks/porto-sdk-python/Makefile" ]; then \
		cd sdks/porto-sdk-python && $(MAKE) clean-deps; \
	fi
	@if [ -d "sdks/porto-sdk-typescript" ] && [ -f "sdks/porto-sdk-typescript/Makefile" ]; then \
		cd sdks/porto-sdk-typescript && $(MAKE) clean-deps; \
	fi
	@echo "  → Removing lab dependencies..."
	@rm -rf labs/*/venv 2>/dev/null || true
	@rm -rf labs/*/node_modules 2>/dev/null || true
	@echo "✅ Dependencies cleaned"

clean-repos: ## Remove cloned SDKs and resources (DESTRUCTIVE - requires re-running setup)
	@echo "⚠️  WARNING: This will remove all cloned SDKs and resources!"
	@echo "   You will need to run 'make' again."
	@read -p "   Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "🧹 Removing SDKs and resources..."; \
		rm -rf sdks/porto-sdk-python 2>/dev/null || true; \
		rm -rf sdks/porto-sdk-typescript 2>/dev/null || true; \
		rm -rf resources/porto-data 2>/dev/null || true; \
		rm -rf resources/porto-features 2>/dev/null || true; \
		echo "✅ SDKs and resources removed"; \
	else \
		echo "❌ Cancelled"; \
		exit 1; \
	fi

clean-all: clean clean-deps ## Clean everything (artifacts + dependencies)
	@echo "✅ Complete clean finished"

clean-nuclear: clean clean-deps clean-repos ## Nuclear clean - removes everything including SDKs and resources (DESTRUCTIVE)
	@echo "✅ Nuclear clean complete - workspace reset to initial state"
