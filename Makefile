# MacroKit Data Lake Management

# Default shell
SHELL := /bin/bash

# Project directories
DATALAKE_DIR := macrokit_datalake
INGEST_DIR := $(DATALAKE_DIR)/ingest
CONFIG_DIR := $(DATALAKE_DIR)/config
DATA_DIR := datalake

# Load .env file
ifneq (,$(wildcard $(DATALAKE_DIR)/.env))
	include $(DATALAKE_DIR)/.env
	export
endif

# Variables
PYTHON := python
CONDA := conda
CONDA_ENV := macrokit

# Configuration
DB_PATH := $(DATA_DIR)/datalake.duckdb
CONFIG_FILE := $(DATALAKE_DIR)/datalake_config.yaml

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
BLUE := \033[0;34m
BOLD := \033[1m
RESET := \033[0m

.PHONY: help setup clean init ingest test check-env check-config list-tables

help: ## Show this help message
	@echo "$(BOLD)MacroKit Data Lake Management$(RESET)"
	@echo "$(BOLD)==============================$(RESET)"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(GREEN)%-20s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

setup: ## Set up conda environment (creates if missing)
	@printf "$(YELLOW)Checking for existing conda environment...$(RESET)\n"
	@if $(CONDA) env list | grep -q "$(CONDA_ENV)"; then \
		printf "$(GREEN)✓ Conda environment '$(CONDA_ENV)' already exists$(RESET)\n"; \
		printf "$(YELLOW)Use 'make setup FORCE=1' to recreate or 'make setup UPDATE=1' to update$(RESET)\n"; \
	else \
		printf "$(YELLOW)Creating new conda environment...$(RESET)\n"; \
		$(CONDA) create -n $(CONDA_ENV) python=3.11 -y; \
		printf "$(YELLOW)Installing core dependencies...$(RESET)\n"; \
		$(CONDA) run -n $(CONDA_ENV) pip install -r requirements.txt; \
		printf "$(GREEN)✓ Environment setup complete$(RESET)\n"; \
		printf "$(YELLOW)Activate with: conda activate $(CONDA_ENV)$(RESET)\n"; \
	fi
	@if [ "$(FORCE)" = "1" ]; then \
		printf "$(YELLOW)Force recreating conda environment...$(RESET)\n"; \
		$(CONDA) env remove -n $(CONDA_ENV) -y 2>/dev/null || true; \
		$(CONDA) create -n $(CONDA_ENV) python=3.11 -y; \
		$(CONDA) run -n $(CONDA_ENV) pip install -r requirements.txt; \
		printf "$(GREEN)✓ Environment recreated$(RESET)\n"; \
	fi
	@if [ "$(UPDATE)" = "1" ]; then \
		printf "$(YELLOW)Updating conda environment packages...$(RESET)\n"; \
		$(CONDA) run -n $(CONDA_ENV) pip install -r requirements.txt --upgrade; \
		printf "$(GREEN)✓ Environment updated$(RESET)\n"; \
	fi

check-conda-env: ## Check if conda environment exists
	@if ! $(CONDA) env list | grep -q "$(CONDA_ENV)"; then \
		printf "$(RED)✗ Conda environment '$(CONDA_ENV)' not found. Run 'make setup'$(RESET)\n"; \
		exit 1; \
	fi

check-env: check-conda-env ## Check if environment variables are set
	@if [ -z "$$FRED_API_KEY" ]; then \
		printf "$(RED)✗ FRED_API_KEY not set. Please add to .env file$(RESET)\n"; \
		exit 1; \
	fi

check-config: ## Check if configuration file exists
	@if [ ! -f "$(CONFIG_FILE)" ]; then \
		printf "$(RED)✗ Configuration file not found: $(CONFIG_FILE)$(RESET)\n"; \
		exit 1; \
	fi

env-info: ## Show conda environment info
	@printf "$(YELLOW)Conda Environment Info:$(RESET)\n"
	@$(CONDA) info --envs
	@echo ""
	@if $(CONDA) env list | grep -q "$(CONDA_ENV)"; then \
		printf "$(YELLOW)Environment '$(CONDA_ENV)' packages:$(RESET)\n"; \
		$(CONDA) list -n $(CONDA_ENV); \
	fi

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

init: check-conda-env check-config ## Initialize the data lake (OVERWRITE=1 for clean slate)
	@printf "$(YELLOW)Initializing data lake...$(RESET)\n"
	@CMD="$(CONDA) run -n $(CONDA_ENV) python $(INGEST_DIR)/initialize.py"; \
	if [ "$(OVERWRITE)" = "1" ]; then CMD="$$CMD --overwrite"; fi; \
	$$CMD
	@printf "$(GREEN)✓ Data lake initialized$(RESET)\n"

# ============================================================================
# DATA INGESTION
# ============================================================================

ingest: check-env ## Ingest data (FULL=1 for historical, OVERWRITE=1 to overwrite, TABLES=name for specific table, START_DATE=YYYY-MM-DD, END_DATE=YYYY-MM-DD)
		@printf "$(YELLOW)Ingesting data...$(RESET)\n"
		@CMD="$(CONDA) run -n $(CONDA_ENV) python $(INGEST_DIR)/raw.py"; \
		if [ "$(FULL)" != "1" ]; then CMD="$$CMD --update_only"; fi; \
		if [ "$(OVERWRITE)" = "1" ]; then CMD="$$CMD --overwrite"; fi; \
		if [ -n "$(TABLES)" ]; then CMD="$$CMD --tables=$(TABLES)"; fi; \
		if [ -n "$(START_DATE)" ]; then CMD="$$CMD --start_date=$(START_DATE)"; fi; \
		if [ -n "$(END_DATE)" ]; then CMD="$$CMD --end_date=$(END_DATE)"; fi; \
		$$CMD
		@printf "$(GREEN)✓ Data ingestion complete$(RESET)\n"

# ============================================================================
# DBT OPERATIONS
# ============================================================================

dbt-run: check-conda-env ## Run dbt models (SELECT=path for specific models, e.g., SELECT=staging)
	@printf "$(YELLOW)Running dbt models...$(RESET)\n"
	@CMD="cd $(DATALAKE_DIR) && $(CONDA) run -n $(CONDA_ENV) dbt run --profiles-dir ."; \
	if [ -n "$(SELECT)" ]; then CMD="$$CMD --select $(SELECT)"; fi; \
	$$CMD
	@printf "$(GREEN)✓ dbt models executed$(RESET)\n"

dbt-test: check-conda-env ## Run dbt tests
	@printf "$(YELLOW)Running dbt tests...$(RESET)\n"
	cd $(DATALAKE_DIR) && $(CONDA) run -n $(CONDA_ENV) dbt test --profiles-dir .
	@printf "$(GREEN)✓ dbt tests completed$(RESET)\n"

dbt-build: check-conda-env ## Build (run + test) all dbt models (CLEAN=1 for fresh build)
	@if [ "$(CLEAN)" = "1" ]; then \
		printf "$(YELLOW)Cleaning dbt artifacts...$(RESET)\n"; \
		cd $(DATALAKE_DIR) && $(CONDA) run -n $(CONDA_ENV) dbt clean --profiles-dir .; \
	fi
	@printf "$(YELLOW)Building dbt models (run + test)...$(RESET)\n"
	cd $(DATALAKE_DIR) && $(CONDA) run -n $(CONDA_ENV) dbt build --profiles-dir .
	@printf "$(GREEN)✓ dbt build completed$(RESET)\n"

dbt-docs: check-conda-env ## Generate dbt documentation (SERVE=1 to start server)
	@if [ ! -f "$(DATALAKE_DIR)/profiles.yml" ]; then \
		printf "$(YELLOW)Creating dbt profiles.yml...$(RESET)\n"; \
		$(MAKE) dbt-setup-profiles; \
	fi
	@printf "$(YELLOW)Generating dbt documentation...$(RESET)\n"
	cd $(DATALAKE_DIR) && $(CONDA) run -n $(CONDA_ENV) dbt docs generate --profiles-dir .
	@printf "$(GREEN)✓ dbt documentation generated$(RESET)\n"
	@if [ "$(SERVE)" = "1" ]; then \
		printf "$(YELLOW)Starting dbt documentation server...$(RESET)\n"; \
		printf "$(GREEN)Documentation available at: http://localhost:8080$(RESET)\n"; \
		printf "$(YELLOW)Press Ctrl+C to stop the server$(RESET)\n"; \
		cd $(DATALAKE_DIR) && $(CONDA) run -n $(CONDA_ENV) dbt docs serve --profiles-dir . --port 8080; \
	fi

# ============================================================================
# STATUS & TESTING
# ============================================================================

status: ## Show project status
	@printf "$(BOLD)Project Status:$(RESET)\n"
	@printf "Conda Environment: "
	@if $(CONDA) env list | grep -q "$(CONDA_ENV)"; then \
		printf "$(GREEN)✓ $(CONDA_ENV) exists$(RESET)\n"; \
	else \
		printf "$(RED)✗ $(CONDA_ENV) missing$(RESET)\n"; \
	fi
	@printf "Configuration: "
	@if [ -f "$(CONFIG_FILE)" ]; then \
		printf "$(GREEN)✓ Found$(RESET)\n"; \
	else \
		printf "$(RED)✗ Missing$(RESET)\n"; \
	fi
	@printf "Database: "
	@if [ -f "$(DB_PATH)" ]; then \
		printf "$(GREEN)✓ Created$(RESET)\n"; \
	else \
		printf "$(RED)✗ Missing$(RESET)\n"; \
	fi
	@printf "FRED API Key: "
	@if [ -n "$$FRED_API_KEY" ]; then \
		printf "$(GREEN)✓ Set$(RESET)\n"; \
	else \
		printf "$(RED)✗ Missing$(RESET)\n"; \
	fi
	@if [ -f "$(DB_PATH)" ]; then $(MAKE) count-records; fi

test: check-conda-env ## Run tests
	@printf "$(YELLOW)Running tests...$(RESET)\n"
	$(CONDA) run -n $(CONDA_ENV) python -m pytest tests/ -v
	@printf "$(GREEN)✓ Tests complete$(RESET)\n"

# ============================================================================
# CLEANUP
# ============================================================================

clean: ## Clean up generated files and cache
	@printf "$(YELLOW)Cleaning up...$(RESET)\n"
	rm -rf $(DATALAKE_DIR)/__pycache__
	rm -rf $(DATALAKE_DIR)/.pytest_cache
	rm -rf $(DATALAKE_DIR)/*.egg-info
	find $(DATALAKE_DIR) -name "*.pyc" -delete
	find $(DATALAKE_DIR) -name "*.pyo" -delete
	@printf "$(GREEN)✓ Cleanup complete$(RESET)\n"

reset: ## Reset everything (dangerous!)
	@printf "$(RED)This will delete ALL data and start fresh!$(RESET)\n"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		printf "$(YELLOW)Resetting everything...$(RESET)\n"; \
		rm -rf $(DATA_DIR); \
		if $(CONDA) env list | grep -q "$(CONDA_ENV)"; then \
			$(CONDA) env remove -n $(CONDA_ENV) -y; \
		fi; \
		printf "$(GREEN)✓ Reset complete$(RESET)\n"; \
	else \
		printf "$(YELLOW)Reset cancelled$(RESET)\n"; \
	fi

dashboard: ## Start Streamlit dashboard
	@printf "$(YELLOW)Starting Streamlit dashboard...$(RESET)\n"
	streamlit run dashboards/app.py
	@printf "$(GREEN)✓ Streamlit dashboard stopped$(RESET)\n"