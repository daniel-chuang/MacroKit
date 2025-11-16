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

flags.DEFINE_boolean(
    "fetch_vintages",
    False,
    "Fetch all historical vintages from ALFRED",
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


def get_date_range():
    """Get start and end dates based on flags"""
    if FLAGS.start_date:
        start_date = validate_date(FLAGS.start_date, "start_date")
        logging.info(f"Using explicit start date: {start_date}")
    elif FLAGS.update_only:
        # start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
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
        "DGS5": "5Y",
        "DGS10": "10Y",
        "DGS30": "30Y",
    }

    for series_id, maturity in treasury_series.items():
        try:
            # Fetch data from FRED
            data = fred.get_series(
                series_id, observation_start=start_date, observation_end=end_date
            )
            logging.info(f"Downloaded: {maturity} Treasury ({len(data)} observations)")

            # Process data
            df = data.reset_index()
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

        except Exception as e:
            logging.error(f"Error processing {maturity} Treasury: {e}")

    logging.info("Ingested treasury yields")


def ingest_economic_indicators(conn, fred_api_key):
    """Ingest economic indicators into database with bitemporal schema"""
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
            # Fetch data from FRED
            data = fred.get_series(
                series_id, observation_start=start_date, observation_end=end_date
            )
            logging.info(
                f"Downloaded: {series_info['indicator']} ({len(data)} observations)"
            )

            # Process data
            df = data.reset_index()
            df.columns = ["date", "value"]

            # Convert to datetime for easier manipulation
            df["date"] = pd.to_datetime(df["date"])

            # Add business time dimensions based on frequency
            if series_info["frequency"] == "QUARTERLY":
                # For quarterly data: Q1 = Jan 1 - Mar 31, Q2 = Apr 1 - Jun 30, etc.
                df["period_start"] = df["date"].dt.to_period("Q").dt.start_time.dt.date
                df["period_end"] = df["date"].dt.to_period("Q").dt.end_time.dt.date
                df["period"] = df["date"].dt.to_period("Q").astype(str)

            elif series_info["frequency"] == "MONTHLY":
                # For monthly data: start = first day of month, end = last day of month
                df["period_start"] = df["date"].dt.to_period("M").dt.start_time.dt.date
                df["period_end"] = df["date"].dt.to_period("M").dt.end_time.dt.date
                df["period"] = df["date"].dt.strftime("%Y-%m")

            elif series_info["frequency"] == "DAILY":
                # For daily data: start and end are the same day
                df["period_start"] = df["date"].dt.date
                df["period_end"] = df["date"].dt.date
                df["period"] = df["date"].dt.strftime("%Y-%m-%d")

            else:
                # Default to daily
                df["period_start"] = df["date"].dt.date
                df["period_end"] = df["date"].dt.date
                df["period"] = df["date"].dt.strftime("%Y-%m-%d")

            df["frequency"] = series_info["frequency"]

            # Add system time dimensions
            # For FRED data, the observation date is typically when it's released
            df["release_date"] = df["date"].dt.date
            df["version_date"] = datetime.now()
            df["is_current"] = True

            # Add data attributes
            df["country"] = "US"
            df["indicator"] = series_info["indicator"]
            df["unit"] = series_info["unit"]

            # Add metadata
            df["source"] = "FRED"
            df["is_revised"] = False  # Initial assumption
            df["revision_type"] = "FINAL"  # FRED typically provides final data

            # Reorder columns to match schema
            df = df[
                [
                    # Data attributes
                    "country",
                    "indicator",
                    "period",
                    "value",
                    "unit",
                    # Metadata
                    "source",
                    "is_revised",
                    "revision_type",
                    # Business time dimensions
                    "period_start",
                    "period_end",
                    "frequency",
                    # System time dimensions
                    "release_date",
                    "version_date",
                    "is_current",
                ]
            ]

            if FLAGS.update_only and not FLAGS.start_date:
                # Mark old versions as not current before inserting new ones
                try:
                    last_date_result = conn.execute(
                        """SELECT MAX(period_start) 
                           FROM economic_indicators 
                           WHERE indicator = ? 
                           AND source = ?
                           AND country = ?""",
                        [series_info["indicator"], "FRED", "US"],
                    ).fetchone()

                    last_date = last_date_result[0] if last_date_result[0] else None

                    if last_date:
                        # Filter for new data
                        new_data = df[df["period_start"] > last_date]

                        if len(new_data) == 0:
                            logging.info(f"No new data for {series_info['indicator']}")
                            continue

                        # Check if any existing data needs to be updated (revisions)
                        existing_dates = df[df["period_start"] <= last_date]

                        if len(existing_dates) > 0:
                            # Mark existing versions as not current
                            for date in existing_dates["period_start"].unique():
                                conn.execute(
                                    """UPDATE economic_indicators 
                                       SET is_current = false
                                       WHERE indicator = ? 
                                       AND source = ?
                                       AND country = ?
                                       AND period_start = ?
                                       AND is_current = true""",
                                    [series_info["indicator"], "FRED", "US", date],
                                )

                            # Mark revised data
                            existing_dates = existing_dates.copy()
                            existing_dates["is_revised"] = True
                            existing_dates["revision_type"] = "REVISED"

                            # Combine new and revised data
                            df = pd.concat(
                                [new_data, existing_dates], ignore_index=True
                            )

                            logging.info(
                                f"Inserting {len(new_data)} new records and "
                                f"{len(existing_dates)} revised records for {series_info['indicator']}"
                            )
                        else:
                            df = new_data
                            logging.info(
                                f"Inserting {len(df)} new records for {series_info['indicator']}"
                            )
                except Exception as e:
                    logging.error(
                        f"Error checking last date for {series_info['indicator']}: {e}, "
                        f"proceeding with full insert"
                    )

            # Insert into DuckDB
            conn.execute("INSERT INTO economic_indicators SELECT * FROM df")
            logging.info(f"Inserted {len(df)} records for {series_info['indicator']}")

        except Exception as e:
            logging.error(f"Error processing {series_info['indicator']}: {e}")

    logging.info("Ingested economic indicators")


def ingest_economic_indicators_with_vintages(conn, fred_api_key):
    """Ingest economic indicators with all historical vintages from ALFRED"""
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
            # This returns a Series with multi-index: (date, realtime_start)
            # The values are the observations as they appeared at each vintage date
            all_releases = fred.get_series_all_releases(series_id)

            if all_releases is None or len(all_releases) == 0:
                logging.warning(
                    f"No vintage data available for {series_info['indicator']}"
                )
                continue

            # Convert to DataFrame and reset index to access the multi-index values
            df_all = all_releases.reset_index()

            # The DataFrame has columns: date, realtime_start, value (and sometimes realtime_end)
            # date = the observation date (e.g., Q1 2020 for GDP)
            # realtime_start = the vintage date (when this value became available)
            # value = the actual data value as it appeared in that vintage

            logging.info(
                f"  Retrieved {len(df_all)} total observations across all vintages"
            )

            # Extract unique vintage dates (realtime_start dates)
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
                    # Filter to rows where realtime_start == vintage_date
                    vintage_df = df_all[df_all["realtime_start"] == vintage_date].copy()

                    if len(vintage_df) == 0:
                        continue

                    # Convert date column to datetime
                    vintage_df["date"] = pd.to_datetime(vintage_df["date"])

                    # Drop NaN values
                    vintage_df = vintage_df.dropna(subset=["value"])

                    if len(vintage_df) == 0:
                        continue

                    # Add business time dimensions based on frequency
                    if series_info["frequency"] == "QUARTERLY":
                        vintage_df["period_start"] = (
                            vintage_df["date"].dt.to_period("Q").dt.start_time.dt.date
                        )
                        vintage_df["period_end"] = (
                            vintage_df["date"].dt.to_period("Q").dt.end_time.dt.date
                        )
                        vintage_df["period"] = (
                            vintage_df["date"].dt.to_period("Q").astype(str)
                        )
                    elif series_info["frequency"] == "MONTHLY":
                        vintage_df["period_start"] = (
                            vintage_df["date"].dt.to_period("M").dt.start_time.dt.date
                        )
                        vintage_df["period_end"] = (
                            vintage_df["date"].dt.to_period("M").dt.end_time.dt.date
                        )
                        vintage_df["period"] = vintage_df["date"].dt.strftime("%Y-%m")
                    elif series_info["frequency"] == "DAILY":
                        vintage_df["period_start"] = vintage_df["date"].dt.date
                        vintage_df["period_end"] = vintage_df["date"].dt.date
                        vintage_df["period"] = vintage_df["date"].dt.strftime(
                            "%Y-%m-%d"
                        )
                    else:
                        vintage_df["period_start"] = vintage_df["date"].dt.date
                        vintage_df["period_end"] = vintage_df["date"].dt.date
                        vintage_df["period"] = vintage_df["date"].dt.strftime(
                            "%Y-%m-%d"
                        )

                    vintage_df["frequency"] = series_info["frequency"]

                    # System time - the vintage date is when this version became available
                    vintage_df["release_date"] = vintage_df["date"].dt.date
                    vintage_df["version_date"] = pd.to_datetime(vintage_date)

                    # Add data attributes
                    vintage_df["country"] = "US"
                    vintage_df["indicator"] = series_info["indicator"]
                    vintage_df["unit"] = series_info["unit"]
                    vintage_df["source"] = "FRED"

                    # Convert to list of dicts
                    for _, row in vintage_df.iterrows():
                        all_records.append(
                            {
                                "period_start": row["period_start"],
                                "period_end": row["period_end"],
                                "period": row["period"],
                                "frequency": row["frequency"],
                                "release_date": row["release_date"],
                                "version_date": row["version_date"],
                                "country": row["country"],
                                "indicator": row["indicator"],
                                "value": float(row["value"]),
                                "unit": row["unit"],
                                "source": row["source"],
                            }
                        )

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

            # Sort by period and version date
            all_vintages_df = all_vintages_df.sort_values(
                ["period_start", "version_date"]
            )

            # Mark which records are current (latest vintage for each period)
            all_vintages_df["is_current"] = False
            latest_idx = all_vintages_df.groupby("period_start")[
                "version_date"
            ].idxmax()
            all_vintages_df.loc[latest_idx, "is_current"] = True

            # Detect revisions
            # If a period has multiple vintages with different values, it's been revised
            def mark_revisions(group):
                # Make a copy to avoid SettingWithCopyWarning
                group = group.copy()

                if len(group) == 1:
                    group["is_revised"] = False
                    group["revision_type"] = "FINAL"
                else:
                    # Check if values actually changed
                    unique_values = group["value"].nunique()
                    if unique_values > 1:
                        # There were actual revisions
                        group["is_revised"] = True
                        # First version is preliminary, last is final, middle are revised
                        revision_types = (
                            ["PRELIMINARY"] + ["REVISED"] * (len(group) - 2) + ["FINAL"]
                        )
                        group["revision_type"] = revision_types
                    else:
                        # Same value across all vintages (no real revision)
                        group["is_revised"] = False
                        group["revision_type"] = "FINAL"
                return group

            all_vintages_df = all_vintages_df.groupby(
                "period_start", group_keys=False
            ).apply(mark_revisions)

            # Reorder columns to match schema
            all_vintages_df = all_vintages_df[
                [
                    # Data attributes
                    "country",
                    "indicator",
                    "period",
                    "value",
                    "unit",
                    # Metadata
                    "source",
                    "is_revised",
                    "revision_type",
                    # Business time dimensions
                    "period_start",
                    "period_end",
                    "frequency",
                    # System time dimensions
                    "release_date",
                    "version_date",
                    "is_current",
                ]
            ]

            # Insert all records
            conn.execute(
                "INSERT INTO economic_indicators SELECT * FROM all_vintages_df"
            )

            # Calculate statistics
            num_periods = all_vintages_df["period_start"].nunique()
            num_vintages = len(all_vintages_df)
            num_revised_periods = all_vintages_df[all_vintages_df["is_revised"]][
                "period_start"
            ].nunique()
            avg_vintages_per_period = (
                num_vintages / num_periods if num_periods > 0 else 0
            )

            logging.info(
                f"✓ Inserted {num_vintages} vintage records for {series_info['indicator']}"
            )
            logging.info(f"  - {num_periods} unique periods")
            logging.info(
                f"  - {num_revised_periods} periods with revisions "
                f"({num_revised_periods/num_periods*100:.1f}%)"
            )
            logging.info(f"  - {avg_vintages_per_period:.1f} avg vintages per period")

        except Exception as e:
            logging.error(f"Error processing {series_info['indicator']}: {e}")
            import traceback

            logging.error(traceback.format_exc())

    logging.info("Completed ingestion of economic indicators with vintages")


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

        # Add partitioning columns based on table schema
        if table == "economic_indicators":
            # Economic indicators use period_start instead of date
            conn.execute(
                f"""
                CREATE OR REPLACE VIEW {table}_with_partitions AS
                SELECT *, 
                       YEAR(period_start) as year, 
                       MONTH(period_start) as month 
                FROM {table}
                """
            )
            partition_cols = "(country, year, month)"
        elif table in ["treasury_yields", "swap_rates", "reference_rates"]:
            # Market data tables use date column
            conn.execute(
                f"""
                CREATE OR REPLACE VIEW {table}_with_partitions AS
                SELECT *, 
                       YEAR(date) as year, 
                       MONTH(date) as month 
                FROM {table}
                """
            )
            partition_cols = "(country, year, month)"
        else:
            # Default partitioning for unknown tables (just year/month)
            conn.execute(
                f"""
                CREATE OR REPLACE VIEW {table}_with_partitions AS
                SELECT *, 
                       YEAR(date) as year, 
                       MONTH(date) as month 
                FROM {table}
                """
            )
            partition_cols = "(year, month)"

        # Export the view with appropriate overwrite setting
        if FLAGS.update_only or overwrite:
            query = f"""
            COPY {table}_with_partitions 
            TO '{output_path}' 
            (FORMAT PARQUET, PARTITION_BY {partition_cols}, OVERWRITE_OR_IGNORE true)
            """
        else:
            query = f"""
            COPY {table}_with_partitions 
            TO '{output_path}' 
            (FORMAT PARQUET, PARTITION_BY {partition_cols})
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

    # Ingest data based on tables flag
    logging.info("\nIngesting data into database...")

    # Parse which tables to ingest
    tables_to_ingest = [table.strip().lower() for table in FLAGS.tables.split(",")]

    # Check if we should ingest all tables or specific ones
    ingest_all = "all" in tables_to_ingest

    if ingest_all or "treasury_yields" in tables_to_ingest:
        logging.info("Ingesting treasury yields...")
        ingest_treasury_yields(conn, fred_api_key)

    if ingest_all or "economic_indicators" in tables_to_ingest:
        if FLAGS.fetch_vintages:
            logging.info(
                "Ingesting economic indicators WITH VINTAGES (this may take a while)..."
            )
            ingest_economic_indicators_with_vintages(conn, fred_api_key)
        else:
            logging.info("Ingesting economic indicators (current data only)...")
            ingest_economic_indicators(conn, fred_api_key)

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
