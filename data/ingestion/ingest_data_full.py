import duckdb
import pandas as pd
from fredapi import Fred
from datetime import datetime, timedelta
import yaml
import os
from dotenv import load_dotenv
from absl import app
from absl import flags
from absl import logging
import shutil

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
    with open("config/database/datalake_config.yaml", "r") as f:
        return yaml.safe_load(f)


def validate_date(date_string, param_name):
    """Validate date string format"""
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError(
            f"{param_name} must be in YYYY-MM-DD format, got: {date_string}"
        )


def get_fred_data(fred_api_key):
    """Fetch economic data from FRED"""
    fred = Fred(api_key=fred_api_key)

    indicators = {
        "DGS1MO": "1-Month Treasury",
        "DGS3MO": "3-Month Treasury",
        "DGS6MO": "6-Month Treasury",
        "DGS1": "1-Year Treasury",
        "DGS2": "2-Year Treasury",
        "DGS5": "5-Year Treasury",
        "DGS10": "10-Year Treasury",
        "DGS30": "30-Year Treasury",
        "DFF": "Federal Funds Rate",
        "GDP": "GDP",
        "CPIAUCSL": "CPI",
        "UNRATE": "Unemployment Rate",
    }

    # Determine start and end dates based on flags
    if FLAGS.start_date:
        # If start_date is explicitly provided, use it
        start_date = validate_date(FLAGS.start_date, "start_date")
        logging.info(f"Using explicit start date: {start_date}")
    elif FLAGS.update_only:
        # If update_only mode, fetch last 30 days
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        logging.info(f"Update mode: fetching data from {start_date}")
    else:
        # Default: full historical data
        start_date = "2010-01-01"
        logging.info(f"Full mode: fetching data from {start_date}")

    # Handle end date
    if FLAGS.end_date:
        end_date = validate_date(FLAGS.end_date, "end_date")
        logging.info(f"Using explicit end date: {end_date}")
    else:
        end_date = datetime.now().strftime("%Y-%m-%d")
        logging.info(f"End date: {end_date}")

    data_dict = {}

    for series_id, name in indicators.items():
        try:
            data = fred.get_series(
                series_id, observation_start=start_date, observation_end=end_date
            )
            data_dict[series_id] = data
            logging.info(f"Downloaded: {name} ({len(data)} observations)")
        except Exception as e:
            logging.error(f"Error downloading {name}: {e}")

    return data_dict


def ingest_treasury_yields(conn, fred_data):
    """Ingest treasury yield data into database"""
    treasury_series = {
        "DGS1MO": "1M",
        "DGS3MO": "3M",
        "DGS6MO": "6M",
        "DGS1": "1Y",
        "DGS2": "2Y",
        "DGS5": "5Y",
        "DGS10": "10Y",
        "DGS30": "30Y",
    }

    for series_id, maturity in treasury_series.items():
        if series_id in fred_data:
            df = fred_data[series_id].reset_index()
            df.columns = ["date", "yield"]
            df["maturity"] = maturity
            df["country"] = "US"
            df = df[["date", "country", "maturity", "yield"]]
            df["date"] = pd.to_datetime(df["date"]).dt.date

            if FLAGS.update_only and not FLAGS.start_date:
                # Only filter by existing data if in update_only mode
                # AND no explicit start_date was provided
                last_date = conn.execute(
                    "SELECT MAX(date) FROM treasury_yields WHERE maturity = ? AND country = ?",
                    [maturity, "US"],
                ).fetchone()[0]

                if last_date:
                    df = df[df["date"] > last_date]
                    if len(df) == 0:
                        logging.info(f"No new data for US {maturity} treasury yields")
                        continue
                    logging.info(
                        f"Inserting {len(df)} new records for US {maturity} "
                        f"(from {df['date'].min()} to {df['date'].max()})"
                    )

            # Insert into DuckDB
            conn.execute("INSERT INTO treasury_yields SELECT * FROM df")
            logging.info(f"Inserted {len(df)} records for US {maturity}")

    logging.info("Ingested treasury yields")


def ingest_economic_indicators(conn, fred_data):
    """Ingest economic indicators into database"""
    econ_series = {
        "DFF": "Federal Funds Rate",
        "GDP": "GDP",
        "CPIAUCSL": "CPI",
        "UNRATE": "Unemployment Rate",
    }

    for series_id, indicator_name in econ_series.items():
        if series_id in fred_data:
            df = fred_data[series_id].reset_index()
            df.columns = ["date", "value"]
            df["indicator"] = indicator_name
            df["release"] = "FRED"
            df = df[["date", "indicator", "value", "release"]]

            if FLAGS.update_only and not FLAGS.start_date:
                # Only filter by existing data if in update_only mode
                # AND no explicit start_date was provided
                try:
                    last_date_result = conn.execute(
                        "SELECT MAX(date) FROM economic_indicators WHERE indicator = ? AND release = ?",
                        [indicator_name, "FRED"],
                    ).fetchone()

                    last_date = last_date_result[0] if last_date_result[0] else None

                    if last_date:
                        df = df[df["date"] > last_date]
                        if len(df) == 0:
                            logging.info(f"No new data for {indicator_name}")
                            continue
                        logging.info(
                            f"Updating {len(df)} new records for {indicator_name}"
                        )
                except Exception as e:
                    logging.info(
                        f"Error checking last date for {indicator_name}: {e}, proceeding with full insert"
                    )

            # Insert into DuckDB
            conn.execute("INSERT INTO economic_indicators SELECT * FROM df")
            logging.info(f"Inserted {len(df)} records for {indicator_name}")

    logging.info("Ingested economic indicators")


def export_to_parquet(conn, config, tables, overwrite):
    """Export tables to parquet files"""
    parquet_path = config["storage"]["local_path"]

    for table in tables:
        output_path = f"{parquet_path}/{table}"

        # Handle different modes
        if os.path.exists(output_path) and not overwrite and not FLAGS.update_only:
            logging.info(
                f"Skipping {table} - data already exists (use --overwrite to overwrite)"
            )
            continue

        # Create directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)

        # Only remove existing files if explicitly overwriting (not in update mode)
        if overwrite and not FLAGS.update_only:
            shutil.rmtree(output_path)
            os.makedirs(output_path, exist_ok=True)
            logging.info(f"Removed existing data for {table}")

        if FLAGS.update_only:
            logging.info(f"Update mode: appending new data to {table} parquet files")

        # Add year and month columns for partitioning
        conn.execute(
            f"""
        CREATE OR REPLACE VIEW {table}_with_partitions AS
        SELECT *, 
               YEAR(date) as year, 
               MONTH(date) as month 
        FROM {table}
        """
        )

        # Export the view with appropriate overwrite setting
        if FLAGS.update_only or overwrite:
            # In update mode or overwrite mode, use OVERWRITE_OR_IGNORE to handle existing partitions
            query = f"""
            COPY {table}_with_partitions 
            TO '{output_path}' 
            (FORMAT PARQUET, PARTITION_BY (year, month), OVERWRITE_OR_IGNORE true)
            """
        else:
            # Initial load - no overwrite needed
            query = f"""
            COPY {table}_with_partitions 
            TO '{output_path}' 
            (FORMAT PARQUET, PARTITION_BY (year, month))
            """

        conn.execute(query)
        logging.info(f"Exported {table} to parquet")

        # Clean up the temporary view
        conn.execute(f"DROP VIEW {table}_with_partitions")


def main(argv):
    logging.info("=" * 60)
    logging.info("MacroKit Initial Data Ingestion")
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

    # Fetch data from FRED
    logging.info("\nFetching data from FRED...")
    fred_data = get_fred_data(fred_api_key)

    # Ingest data based on tables flag
    logging.info("\nIngesting data into database...")

    # Parse which tables to ingest
    tables_to_ingest = [table.strip().lower() for table in FLAGS.tables.split(",")]

    # Check if we should ingest all tables or specific ones
    ingest_all = "all" in tables_to_ingest

    if ingest_all or "treasury_yields" in tables_to_ingest:
        logging.info("Ingesting treasury yields...")
        ingest_treasury_yields(conn, fred_data)

    if ingest_all or "economic_indicators" in tables_to_ingest:
        logging.info("Ingesting economic indicators...")
        ingest_economic_indicators(conn, fred_data)

    # Export to parquet
    logging.info("\nExporting to parquet files...")
    export_to_parquet(conn, config, tables_to_ingest, FLAGS.overwrite)

    # Close connection
    conn.close()

    logging.info("\n" + "=" * 60)
    logging.info("Initial data ingestion completed!")
    logging.info("=" * 60)


if __name__ == "__main__":
    app.run(main)
