.PHONY: run test docs clean seed debug help

PROFILES_DIR := .

help:
	@echo "MacroKit Datalake - Available Commands:"
	@echo "  make debug        - Test database connection"
	@echo "  make seed         - Load reference data"
	@echo "  make run          - Run all dbt models"
	@echo "  make test         - Run all tests"
	@echo "  make docs         - Generate and serve documentation"
	@echo "  make clean        - Clean build artifacts"

debug:
	dbt debug --profiles-dir $(PROFILES_DIR)

seed:
	dbt seed --profiles-dir $(PROFILES_DIR)

run:
	dbt run --profiles-dir $(PROFILES_DIR)

test:
	dbt test --profiles-dir $(PROFILES_DIR)

docs:
	dbt docs generate --profiles-dir $(PROFILES_DIR)
	dbt docs serve --profiles-dir $(PROFILES_DIR)

clean:
	dbt clean --profiles-dir $(PROFILES_DIR)