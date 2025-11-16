# MacroKit Data Lake Management

# Default shell
SHELL := /bin/bash

# Project directories (updated for parent directory)
DATALAKE_DIR := macrokit_datalake
INGEST_DIR := $(DATALAKE_DIR)/ingest
CONFIG_DIR := $(DATALAKE_DIR)/config
DATA_DIR := datalake

# Load .env file
ifneq (,$(wildcard $(DATALAKE_DIR)/.env))
		include $(DATALAKE_DIR)/.env
		export
endif

# Variables - Updated for Conda
PYTHON := python
CONDA := conda
CONDA_ENV := macrokit
ACTIVATE := conda activate $(CONDA_ENV)


# Configuration (look in datalake directory)
DB_PATH := $(DATA_DIR)/datalake.duckdb
CONFIG_FILE := $(DATALAKE_DIR)/datalake_config.yaml

# Colors for output - Fixed for better terminal compatibility
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
		@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(GREEN)%-15s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Set up conda environment (only if it doesn't exist)
		@printf "$(YELLOW)Checking for existing conda environment...$(RESET)\n"
		@if $(CONDA) env list | grep -q "$(CONDA_ENV)"; then \
				printf "$(GREEN)✓ Conda environment '$(CONDA_ENV)' already exists$(RESET)\n"; \
				printf "$(YELLOW)Use 'make setup-force' to recreate or 'make setup-update' to update packages$(RESET)\n"; \
		else \
				printf "$(YELLOW)Creating new conda environment...$(RESET)\n"; \
				$(CONDA) create -n $(CONDA_ENV) python=3.11 -y; \
				printf "$(YELLOW)Installing core dependencies...$(RESET)\n"; \
				$(CONDA) run -n $(CONDA_ENV) pip install -r requirements.txt; \
				printf "$(GREEN)✓ Environment setup complete$(RESET)\n"; \
				printf "$(YELLOW)Activate with: conda activate $(CONDA_ENV)$(RESET)\n"; \
		fi

setup-force: ## Force recreate conda environment
		@printf "$(YELLOW)Force recreating conda environment...$(RESET)\n"
		@if $(CONDA) env list | grep -q "$(CONDA_ENV)"; then \
				printf "$(YELLOW)Removing existing environment...$(RESET)\n"; \
				$(CONDA) env remove -n $(CONDA_ENV) -y; \
		fi
		@printf "$(YELLOW)Creating new conda environment...$(RESET)\n"
		$(CONDA) create -n $(CONDA_ENV) python=3.11 -y
		@printf "$(YELLOW)Installing core dependencies...$(RESET)\n"
		$(CONDA) run -n $(CONDA_ENV) pip install -r requirements.txt
		@printf "$(GREEN)✓ Environment setup complete$(RESET)\n"
		@printf "$(YELLOW)Activate with: conda activate $(CONDA_ENV)$(RESET)\n"

setup-update: ## Update existing conda environment packages
		@printf "$(YELLOW)Updating conda environment packages...$(RESET)\n"
		@if $(CONDA) env list | grep -q "$(CONDA_ENV)"; then \
				$(CONDA) run -n $(CONDA_ENV) pip install -r requirements.txt --upgrade; \
				printf "$(GREEN)✓ Environment updated$(RESET)\n"; \
		else \
				printf "$(RED)✗ Environment '$(CONDA_ENV)' not found. Run 'make setup' first.$(RESET)\n"; \
				exit 1; \
		fi

clean: ## Clean up generated files and cache
		@printf "$(YELLOW)Cleaning up...$(RESET)\n"
		rm -rf $(DATALAKE_DIR)/__pycache__
		rm -rf $(DATALAKE_DIR)/.pytest_cache
		rm -rf $(DATALAKE_DIR)/*.egg-info
		find $(DATALAKE_DIR) -name "*.pyc" -delete
		find $(DATALAKE_DIR) -name "*.pyo" -delete
		@printf "$(GREEN)✓ Cleanup complete$(RESET)\n"

clean-env: ## Remove conda environment
		@printf "$(YELLOW)Removing conda environment...$(RESET)\n"
		@if $(CONDA) env list | grep -q "$(CONDA_ENV)"; then \
				$(CONDA) env remove -n $(CONDA_ENV) -y; \
				printf "$(GREEN)✓ Environment removed$(RESET)\n"; \
		else \
				printf "$(YELLOW)Environment '$(CONDA_ENV)' not found$(RESET)\n"; \
		fi

check-conda-env: ## Check if conda environment exists
		@printf "$(YELLOW)Checking conda environment...$(RESET)\n"
		@if $(CONDA) env list | grep -q "$(CONDA_ENV)"; then \
				printf "$(GREEN)✓ Conda environment '$(CONDA_ENV)' exists$(RESET)\n"; \
		else \
				printf "$(RED)✗ Conda environment '$(CONDA_ENV)' not found. Run 'make setup'$(RESET)\n"; \
				exit 1; \
		fi

check-env: check-conda-env ## Check if environment variables are set
		@printf "$(YELLOW)Checking environment variables...$(RESET)\n"
		@if [ -z "$$FRED_API_KEY" ]; then \
				printf "$(RED)✗ FRED_API_KEY not set. Please add to .env file$(RESET)\n"; \
				exit 1; \
		else \
				printf "$(GREEN)✓ FRED_API_KEY is set$(RESET)\n"; \
		fi

check-config: ## Check if configuration file exists
		@printf "$(YELLOW)Checking configuration...$(RESET)\n"
		@if [ ! -f "$(CONFIG_FILE)" ]; then \
				printf "$(RED)✗ Configuration file not found: $(CONFIG_FILE)$(RESET)\n"; \
				exit 1; \
		else \
				printf "$(GREEN)✓ Configuration file found$(RESET)\n"; \
		fi

init: check-conda-env check-config ## Initialize the data lake (create database and tables)
		@printf "$(YELLOW)Initializing data lake...$(RESET)\n"
		$(CONDA) run -n $(CONDA_ENV) python $(INGEST_DIR)/initialize.py
		@printf "$(GREEN)✓ Data lake initialized$(RESET)\n"

init-clean: check-conda-env check-config ## Initialize with clean slate (overwrite existing)
		@printf "$(YELLOW)Initializing data lake (clean slate)...$(RESET)\n"
		$(CONDA) run -n $(CONDA_ENV) python $(INGEST_DIR)/initialize.py --overwrite
		@printf "$(GREEN)✓ Data lake initialized (clean)$(RESET)\n"

init-raw: check-conda-env check-config ## Initialize only raw tables
		@printf "$(YELLOW)Initializing raw tables only...$(RESET)\n"
		$(CONDA) run -n $(CONDA_ENV) python $(INGEST_DIR)/initialize.py --raw_only
		@printf "$(GREEN)✓ Raw tables initialized$(RESET)\n"

ingest: check-env ## Ingest all data (incremental)
		@printf "$(YELLOW)Ingesting all data (incremental)...$(RESET)\n"
		$(CONDA) run -n $(CONDA_ENV) python $(INGEST_DIR)/raw.py --update_only
		@printf "$(GREEN)✓ Data ingestion complete$(RESET)\n"

ingest-force: check-env ## Ingest all data (incremental, overwrite existing)
		@printf "$(YELLOW)Ingesting all data (incremental, overwrite)...$(RESET)\n"
		$(CONDA) run -n $(CONDA_ENV) python $(INGEST_DIR)/raw.py --update_only --overwrite
		@printf "$(GREEN)✓ Data ingestion (overwrite) complete$(RESET)\n"

ingest-full: check-env ## Ingest all data (full historical)
		@printf "$(YELLOW)Ingesting all data (full historical)...$(RESET)\n"
		$(CONDA) run -n $(CONDA_ENV) python $(INGEST_DIR)/raw.py
		@printf "$(GREEN)✓ Full data ingestion complete$(RESET)\n"

ingest-full-force: check-env ## Ingest all data (full historical, overwrite existing)
		@printf "$(YELLOW)Ingesting all data (full historical, overwrite)...$(RESET)\n"
		$(CONDA) run -n $(CONDA_ENV) python $(INGEST_DIR)/raw.py --overwrite
		@printf "$(GREEN)✓ Full data ingestion (overwrite) complete$(RESET)\n"

ingest-treasury: check-env ## Ingest only treasury yields
		@printf "$(YELLOW)Ingesting treasury yields...$(RESET)\n"
		$(CONDA) run -n $(CONDA_ENV) python $(INGEST_DIR)/raw.py --tables=treasury_yields --update_only
		@printf "$(GREEN)✓ Treasury yields ingested$(RESET)\n"

ingest-econ: check-env ## Ingest economic indicators
		@printf "$(YELLOW)Ingesting economic indicators...$(RESET)\n"
		$(CONDA) run -n $(CONDA_ENV) python $(INGEST_DIR)/raw.py --tables=economic_indicators --update_only
		@printf "$(GREEN)✓ Economic indicators ingested$(RESET)\n"

list-tables: check-conda-env ## Show all tables in the database
		@printf "$(YELLOW)Tables in database:$(RESET)\n"
		@if [ -f "$(DB_PATH)" ]; then \
				$(CONDA) run -n $(CONDA_ENV) python -c "import duckdb; conn=duckdb.connect('$(DB_PATH)'); print('\n'.join([f'  - {row[0]}' for row in conn.execute('SHOW TABLES').fetchall()])); conn.close()"; \
		else \
				printf "$(RED)✗ Database not found. Run 'make init' first.$(RESET)\n"; \
		fi

count-records: check-conda-env ## Count records in all tables
		@printf "$(YELLOW)Record counts:$(RESET)\n"
		@if [ -f "$(DB_PATH)" ]; then \
				$(CONDA) run -n $(CONDA_ENV) python -c "\
import duckdb; \
conn=duckdb.connect('$(DB_PATH)'); \
tables = [row[0] for row in conn.execute('SHOW TABLES').fetchall()]; \
for table in tables: \
		try: \
				count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]; \
				print(f'  {table}: {count:,} records'); \
		except: \
				print(f'  {table}: Error counting'); \
conn.close()"; \
		else \
				printf "$(RED)✗ Database not found. Run 'make init' first.$(RESET)\n"; \
		fi

test: check-conda-env ## Run tests
		@printf "$(YELLOW)Running tests...$(RESET)\n"
		$(CONDA) run -n $(CONDA_ENV) python -m pytest tests/ -v
		@printf "$(GREEN)✓ Tests complete$(RESET)\n"

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
		@if [ -f "$(DB_PATH)" ]; then make count-records; fi

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

# Quick development workflows
quick-start: setup check-config init ingest-treasury ## Quick start: setup + init + treasury data
		@printf "$(GREEN)✓ Quick start complete! Treasury data loaded.$(RESET)\n"

daily-update: check-env ingest count-records ## Daily workflow: update all data
		@printf "$(GREEN)✓ Daily update complete!$(RESET)\n"

# Development helpers
shell: check-conda-env ## Open Python shell with database connection
		@printf "$(YELLOW)Opening Python shell with database connection...$(RESET)\n"
		$(CONDA) run -n $(CONDA_ENV) python -c "\
import duckdb; \
conn = duckdb.connect('$(DB_PATH)'); \
print('Database connection available as: conn'); \
print('Example: conn.execute(\"SHOW TABLES\").fetchall()'); \
import code; \
code.interact(local=locals())"

env-info: ## Show conda environment info
		@printf "$(YELLOW)Conda Environment Info:$(RESET)\n"
		@$(CONDA) info --envs
		@echo ""
		@if $(CONDA) env list | grep -q "$(CONDA_ENV)"; then \
				printf "$(YELLOW)Environment '$(CONDA_ENV)' packages:$(RESET)\n"; \
				$(CONDA) list -n $(CONDA_ENV); \
		else \
				printf "$(RED)Environment '$(CONDA_ENV)' not found$(RESET)\n"; \
		fi

# No-color versions (fallback)
help-plain: ## Show help without colors
		@echo "MacroKit Data Lake Management"
		@echo "============================="
		@echo ""
		@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "%-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

status-plain: ## Show status without colors
		@echo "Project Status:"
		@echo -n "Conda Environment: "
		@if $(CONDA) env list | grep -q "$(CONDA_ENV)"; then \
				echo "OK - $(CONDA_ENV) exists"; \
		else \
				echo "MISSING - $(CONDA_ENV) not found"; \
		fi
		@echo -n "Configuration: "
		@if [ -f "$(CONFIG_FILE)" ]; then \
				echo "OK - Found"; \
		else \
				echo "MISSING"; \
		fi
		@echo -n "Database: "
		@if [ -f "$(DB_PATH)" ]; then \
				echo "OK - Created"; \
		else \
				echo "MISSING"; \
		fi
		@echo -n "FRED API Key: "
		@if [ -n "$$FRED_API_KEY" ]; then \
				echo "OK - Set"; \
		else \
				echo "MISSING"; \
		fi

docs: check-conda-env ## Generate dbt documentation
		@printf "$(YELLOW)Generating dbt documentation...$(RESET)\n"
		@if [ ! -f "$(DATALAKE_DIR)/profiles.yml" ]; then \
				printf "$(YELLOW)Creating dbt profiles.yml...$(RESET)\n"; \
				$(MAKE) dbt-setup-profiles; \
		fi
		cd $(DATALAKE_DIR) && $(CONDA) run -n $(CONDA_ENV) dbt docs generate --profiles-dir .
		@printf "$(GREEN)✓ dbt documentation generated$(RESET)\n"

docs-serve: docs ## Serve dbt documentation locally
		@printf "$(YELLOW)Starting dbt documentation server...$(RESET)\n"
		@printf "$(GREEN)Documentation will be available at: http://localhost:8080$(RESET)\n"
		@printf "$(YELLOW)Press Ctrl+C to stop the server$(RESET)\n"
		cd $(DATALAKE_DIR) && $(CONDA) run -n $(CONDA_ENV) dbt docs serve --profiles-dir . --port 8080