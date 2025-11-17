import duckdb
import os
from dotenv import load_dotenv
from absl import app, flags, logging
import yaml

# Import processors and extractors
from extractors.fred import FREDExtractor
from processors.market import MarketProcessor
from processors.economic import EconomicProcessor
from processors.treasury import TreasuryYieldProcessor

FLAGS = flags.FLAGS

flags.DEFINE_boolean("overwrite", False, "Whether to overwrite existing data")
flags.DEFINE_boolean("update_only", False, "Whether to only update existing data")
flags.DEFINE_string(
    "tables", "all", "Comma-separated list of tables to ingest (default: all)"
)
flags.DEFINE_string(
    "start_date",
    None,
    "Start date for data fetch in YYYY-MM-DD format (overrides update_only)",
)
flags.DEFINE_string(
    "end_date", None, "End date for data fetch in YYYY-MM-DD format (default: today)"
)

load_dotenv()


def load_config():
    """Load configuration from YAML file"""
    with open("macrokit_datalake/datalake_config.yaml", "r") as f:
        return yaml.safe_load(f)


def get_date_range():
    """Get start and end dates based on flags"""
    from datetime import datetime

    if FLAGS.start_date:
        start_date = FLAGS.start_date
        logging.info(f"Using explicit start date: {start_date}")
    elif FLAGS.update_only:
        start_date = "1800-01-01"
        logging.info(f"Update mode: fetching data from {start_date}")
    else:
        start_date = "1800-01-01"
        logging.info(f"Full mode: fetching data from {start_date}")

    if FLAGS.end_date:
        end_date = FLAGS.end_date
        logging.info(f"Using explicit end date: {end_date}")
    else:
        end_date = datetime.now().strftime("%Y-%m-%d")
        logging.info(f"End date: {end_date}")

    return start_date, end_date


def main(argv):
    logging.info("=" * 60)
    logging.info("MacroKit Raw Data Ingestion")
    logging.info("=" * 60)

    # Load configuration
    config = load_config()

    # Connect to database
    db_path = config["database"]["path"]
    conn = duckdb.connect(db_path)

    # Get FRED API key
    fred_api_key = os.getenv("FRED_API_KEY")
    if not fred_api_key:
        raise ValueError("FRED_API_KEY not found in .env file")

    # Initialize extractor
    fred_extractor = FREDExtractor(api_key=fred_api_key)

    # Parse which tables to ingest
    tables_to_ingest = [table.strip().lower() for table in FLAGS.tables.split(",")]
    ingest_all = "all" in tables_to_ingest

    # Get date range
    start_date, end_date = get_date_range()

    logging.info("\nIngesting raw data into database...")

    # Process market data
    if ingest_all or "us_market_data" in tables_to_ingest:
        logging.info("Ingesting market data...")
        market_processor = MarketProcessor(fred_extractor, conn)
        market_processor.process(
            start_date=start_date, end_date=end_date, update_only=FLAGS.update_only
        )

    # Process treasury yields
    if ingest_all or "us_treasury_yields" in tables_to_ingest:
        logging.info("Ingesting treasury yields...")
        treasury_processor = TreasuryYieldProcessor(fred_extractor, conn)
        treasury_processor.process(
            start_date=start_date, end_date=end_date, update_only=FLAGS.update_only
        )

    # Process economic indicators
    if ingest_all or "us_economic_indicators" in tables_to_ingest:
        logging.info("Ingesting economic indicators WITH VINTAGES...")
        economic_processor = EconomicProcessor(fred_extractor, conn)
        economic_processor.process(
            start_date=start_date, end_date=end_date, update_only=FLAGS.update_only
        )

    # Close connection
    conn.close()

    logging.info("=" * 60)
    logging.info("Raw data ingestion completed!")
    logging.info("Next step: Run DBT to transform data (dbt run)")
    logging.info("=" * 60)


if __name__ == "__main__":
    app.run(main)
