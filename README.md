# MacroKit

MacroKit is a comprehensive library for semi-systematic macro trading, with a focus on interest rate products.

Developed by Daniel Chuang

## Usage Setup

1. Create a new conda environment
2. Pip install from requirements.txt

## Development Setup

1. Brew install duckdb (for CLI interface)
2. brew install --cask dbeaver-community (for GUI interface)

## Structure

### analytics/

This folder contains the analytical tools for rates investing, including portfolio management tools, interest rate models, macro analysis, etc.

### data/

Creates a DuckDB datalake, which stores time series data as columnar parquet files. These parquet files will be hosted on a VM and mounted to the local machine so that the data can be easily accessed.

Ingestion will be handled in two stages: setup and update. Setup will initialize the database from scratch, and update will be called on a periodic basis for periodic updates to the datalake.

### datalake/

Where the data is stored.

### backtest/

A backtesting engine.

### web/

A web interface for quick overviews, graphics, etc.

### notebooks/

For research and exploration in a non-productionalized environment.

### config/

Configuration files

### scripts

Helpful scripts.

### tests/

Testing for code.
