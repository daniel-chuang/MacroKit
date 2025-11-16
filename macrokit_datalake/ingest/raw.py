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


def validate_date(date_string, param_name):
    """Validate date string format"""
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError(
            f"{param_name} must be in YYYY-MM-DD format, got: {date_string}"
        )


def get_date_range():
    """Get start and end dates based on flags"""
    if FLAGS.start_date:
        start_date = validate_date(FLAGS.start_date, "start_date")
        logging.info(f"Using explicit start date: {start_date}")
    elif FLAGS.update_only:
        start_date = "1800-01-01"
        logging.info(f"Update mode: fetching data from {start_date}")
    else:
        start_date = "1800-01-01"
        logging.info(f"Full mode: fetching data from {start_date}")

    if FLAGS.end_date:
        end_date = validate_date(FLAGS.end_date, "end_date")
        logging.info(f"Using explicit end date: {end_date}")
    else:
        end_date = datetime.now().strftime("%Y-%m-%d")
        logging.info(f"End date: {end_date}")

    return start_date, end_date


def ingest_treasury_yields(conn, fred_api_key):
    """Ingest treasury yield data into database"""
    fred = Fred(api_key=fred_api_key)
    start_date, end_date = get_date_range()

    treasury_series = {
        "DGS1MO": "1M",
        "DGS3MO": "3M",
        "DGS6MO": "6M",
        "DGS1": "1Y",
        "DGS2": "2Y",
        "DGS3": "3Y",
        "DGS5": "5Y",
        "DGS7": "7Y",
        "DGS10": "10Y",
        "DGS20": "20Y",
        "DGS30": "30Y",
    }

    for series_id, maturity in treasury_series.items():
        try:
            # Fetch data from FRED
            data = fred.get_series(
                series_id, observation_start=start_date, observation_end=end_date
            )
            logging.info(f"Downloaded: {maturity} Treasury ({len(data)} observations)")

            # Process data - minimal transformation, just type conversion
            df = data.reset_index()
            df.columns = ["date", "yield"]
            df["maturity"] = maturity
            df["country"] = "US"
            df["source"] = "FRED"
            df["series_id"] = series_id
            df["_loaded_at"] = datetime.now()

            # Convert date to proper format
            df["date"] = pd.to_datetime(df["date"]).dt.date

            # Reorder columns to match table schema
            df = df[
                [
                    "series_id",
                    "date",
                    "yield",
                    "maturity",
                    "country",
                    "source",
                    "_loaded_at",
                ]
            ]

            if FLAGS.update_only and not FLAGS.start_date:
                # Only filter by existing data if in update_only mode
                # AND no explicit start_date was provided
                last_date = conn.execute(
                    "SELECT MAX(date) FROM raw.treasury_yields WHERE maturity = ? AND country = ?",
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
            conn.execute(
                """
                INSERT INTO raw.treasury_yields (series_id, date, yield, maturity, country, source, _loaded_at)
                SELECT series_id, date, yield, maturity, country, source, _loaded_at FROM df
            """
            )
            logging.info(f"Inserted {len(df)} records for US {maturity}")

        except Exception as e:
            logging.error(f"Error processing {maturity} Treasury: {e}")

    logging.info("Ingested treasury yields")


def ingest_economic_indicators(conn, fred_api_key):
    """
    Ingest economic indicators with all historical vintages from ALFRED.

    This function only handles data extraction and loading - all business logic
    transformations (like is_current flag) will be handled in DBT.
    """
    fred = Fred(api_key=fred_api_key)
    start_date, end_date = get_date_range()

    econ_series = {
        "GDP": {"indicator": "GDP", "frequency": "QUARTERLY", "unit": "BILLIONS"},
        "CPIAUCSL": {"indicator": "CPI", "frequency": "MONTHLY", "unit": "INDEX"},
        "UNRATE": {
            "indicator": "Unemployment Rate",
            "frequency": "MONTHLY",
            "unit": "PERCENT",
        },
    }

    for series_id, series_info in econ_series.items():
        try:
            logging.info(f"Fetching vintage data for {series_info['indicator']}...")

            # Get all releases (vintages) for this series
            all_releases = fred.get_series_all_releases(series_id)

            if all_releases is None or len(all_releases) == 0:
                logging.warning(
                    f"No vintage data available for {series_info['indicator']}"
                )
                continue

            # Convert to DataFrame and reset index
            df_all = all_releases.reset_index()

            logging.info(
                f"  Retrieved {len(df_all)} total observations across all vintages"
            )

            # Extract unique vintage dates from realtime_start
            vintage_dates = sorted(df_all["realtime_start"].unique())

            # Filter vintages to our date range
            vintage_dates = [
                vd
                for vd in vintage_dates
                if pd.to_datetime(start_date).date()
                <= pd.to_datetime(vd).date()
                <= pd.to_datetime(end_date).date()
            ]

            if len(vintage_dates) == 0:
                logging.warning(
                    f"No vintages in date range {start_date} to {end_date} "
                    f"for {series_info['indicator']}"
                )
                continue

            logging.info(
                f"  Found {len(vintage_dates)} vintages between "
                f"{pd.to_datetime(vintage_dates[0]).date()} and "
                f"{pd.to_datetime(vintage_dates[-1]).date()}"
            )

            all_records = []

            # Process each vintage
            for i, vintage_date in enumerate(vintage_dates):
                try:
                    # Get the data as it existed on this vintage date
                    vintage_df = df_all[df_all["realtime_start"] == vintage_date].copy()

                    if len(vintage_df) == 0:
                        continue

                    # Convert date column to datetime
                    vintage_df["date"] = pd.to_datetime(vintage_df["date"])

                    # Drop NaN values
                    vintage_df = vintage_df.dropna(subset=["value"])

                    if len(vintage_df) == 0:
                        continue

                    # Process each record - MINIMAL transformation, just type conversion
                    for _, row in vintage_df.iterrows():
                        # Handle missing realtime_end column
                        realtime_end = row.get("realtime_end")
                        if realtime_end is None or pd.isna(realtime_end):
                            realtime_end = row["realtime_start"]

                        record = {
                            "series_id": series_id,
                            "observation_date": row["date"].date(),
                            "value": float(row["value"]),
                            "realtime_start": pd.to_datetime(
                                row["realtime_start"]
                            ).date(),
                            "realtime_end": pd.to_datetime(realtime_end).date(),
                            "country": "US",
                            "indicator": series_info["indicator"],
                            "unit": series_info["unit"],
                            "source": "FRED",
                            "frequency": series_info["frequency"],
                            "_loaded_at": datetime.now(),
                        }
                        all_records.append(record)

                    # Log progress every 50 vintages
                    if (i + 1) % 50 == 0:
                        logging.info(
                            f"  Processed {i + 1}/{len(vintage_dates)} vintages "
                            f"({len(all_records)} total observations)"
                        )

                except Exception as e:
                    logging.warning(
                        f"  Error processing vintage {pd.to_datetime(vintage_date).date()}: {e}"
                    )
                    continue

            if not all_records:
                logging.warning(
                    f"No vintage records extracted for {series_info['indicator']}"
                )
                continue

            # Convert to DataFrame
            all_vintages_df = pd.DataFrame(all_records)

            # Sort by observation date and realtime_start
            all_vintages_df = all_vintages_df.sort_values(
                ["observation_date", "realtime_start"]
            )

            # Insert all records
            conn.execute(
                """
                INSERT INTO raw.economic_indicators 
                (series_id, observation_date, value, realtime_start, realtime_end, 
                 country, indicator, unit, source, frequency, _loaded_at)
                SELECT series_id, observation_date, value, realtime_start, realtime_end,
                       country, indicator, unit, source, frequency, _loaded_at 
                FROM all_vintages_df
            """
            )

            # Calculate statistics
            num_observations = len(all_vintages_df)
            num_unique_dates = all_vintages_df["observation_date"].nunique()
            num_vintages = all_vintages_df.groupby("observation_date")[
                "realtime_start"
            ].count()
            num_revised = (num_vintages > 1).sum()
            avg_vintages = (
                num_observations / num_unique_dates if num_unique_dates > 0 else 0
            )

            logging.info(
                f"✓ Inserted {num_observations} vintage records for {series_info['indicator']}"
            )
            logging.info(f"  - {num_unique_dates} unique observation dates")
            logging.info(
                f"  - {num_revised} dates with revisions "
                f"({num_revised/num_unique_dates*100:.1f}%)"
            )
            logging.info(f"  - {avg_vintages:.1f} avg vintages per date")

        except Exception as e:
            logging.error(f"Error processing {series_info['indicator']}: {e}")
            import traceback

            logging.error(traceback.format_exc())

    logging.info("Completed ingestion of economic indicators with vintages")


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

    # Parse which tables to ingest
    tables_to_ingest = [table.strip().lower() for table in FLAGS.tables.split(",")]
    ingest_all = "all" in tables_to_ingest

    logging.info("\nIngesting raw data into database...")

    if ingest_all or "treasury_yields" in tables_to_ingest:
        logging.info("Ingesting treasury yields...")
        ingest_treasury_yields(conn, fred_api_key)

    if ingest_all or "economic_indicators" in tables_to_ingest:
        logging.info(
            "Ingesting economic indicators WITH VINTAGES (this may take a while)..."
        )
        ingest_economic_indicators(conn, fred_api_key)

    # Close connection
    conn.close()

    logging.info("\n" + "=" * 60)
    logging.info("Raw data ingestion completed!")
    logging.info("Next step: Run DBT to transform data (dbt run)")
    logging.info("=" * 60)


if __name__ == "__main__":
    app.run(main)
