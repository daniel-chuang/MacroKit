import duckdb
import yaml
from pathlib import Path
from absl import logging
from absl import app
from absl import flags
import shutil
from typing import Dict, List, Any, Optional
import os
from macrokit_datalake import config_utils

FLAGS = flags.FLAGS

flags.DEFINE_boolean("overwrite", False, "Whether to overwrite existing data")


def get_enum_values_from_dbt(
    dbt_path: str = "macrokit_datalake/dbt_project.yml",
) -> Dict[str, List[str]]:
    """Get enum values from the DBT project configuration.

    Args:
        dbt_path: Path to the DBT project YAML file

    Returns:
        Dictionary mapping enum names to their values

    Raises:
        FileNotFoundError: If DBT project file doesn't exist
        KeyError: If 'vars' section is missing from DBT config
    """
    try:
        with open(dbt_path, "r") as f:
            dbt_config = yaml.safe_load(f)

        if "vars" not in dbt_config:
            raise KeyError("'vars' section not found in DBT project configuration")

        return dbt_config["vars"]
    except FileNotFoundError:
        raise FileNotFoundError(f"DBT project file not found: {dbt_path}")


def map_dbt_vars_to_enums(dbt_vars: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Map DBT variable names to database enum names.

    Args:
        dbt_vars: Dictionary of DBT variables

    Returns:
        Dictionary mapping enum names to their values
    """
    enum_mapping = {
        "country_code": dbt_vars.get("country_codes", []),
        "frequency_type": dbt_vars.get("frequency_types", []),
        "revision_type": dbt_vars.get("revision_types", []),
        "currency_code": dbt_vars.get("currency_codes", []),
        "unit_type": dbt_vars.get("unit_types", []),
        "yield_type": dbt_vars.get("yield_types", []),
        "security_type": dbt_vars.get("security_types", []),
        "curve_method": dbt_vars.get("curve_methods", []),
        "source_system": dbt_vars.get("source_systems", []),
        "day_count_convention": dbt_vars.get("day_count_conventions", []),
    }

    # Filter out empty enums
    return {name: values for name, values in enum_mapping.items() if values}


def create_folder_if_not_exists(folder_path: str) -> None:
    """Create folder if it doesn't exist, with optional overwrite.

    Args:
        folder_path: Path to the folder to create
    """
    folder_path_obj = Path(folder_path)

    if FLAGS.overwrite and folder_path_obj.exists():
        logging.info(f"Overwriting existing folder: {folder_path}")
        shutil.rmtree(folder_path)
    else:
        logging.info(f"Creating folder: {folder_path}")

    folder_path_obj.mkdir(parents=True, exist_ok=True)


def create_database(config: Dict[str, Any]) -> duckdb.DuckDBPyConnection:
    """Create or connect to DuckDB database.

    Args:
        config: Configuration dictionary containing database settings

    Returns:
        DuckDB connection object

    Raises:
        KeyError: If required database configuration is missing
    """
    try:
        db_path = config["database"]["path"]
    except KeyError:
        raise KeyError("Database path not found in configuration")

    db_path_obj = Path(db_path)

    if FLAGS.overwrite and db_path_obj.exists():
        logging.info(f"Overwriting existing database: {db_path}")
        db_path_obj.unlink()

    conn = duckdb.connect(db_path)
    logging.info(f"Created DuckDB database at {db_path}")
    return conn


def create_enums(
    conn: duckdb.DuckDBPyConnection, enum_values: Dict[str, List[str]]
) -> None:
    """Create database enums from configuration.

    Args:
        conn: DuckDB connection object
        enum_values: Dictionary mapping enum names to their possible values
    """
    if not enum_values:
        logging.warning("No enum values provided")
        return

    for enum_name, values in enum_values.items():
        if not values:
            logging.warning(f"Skipping empty enum: {enum_name}")
            continue

        # Check if enum already exists
        result = conn.execute(
            f"SELECT 1 FROM duckdb_types() WHERE type_name = '{enum_name}'"
        ).fetchone()

        if result:
            logging.info(f"Enum {enum_name} already exists, skipping")
            continue

        values_str = ", ".join(f"'{v}'" for v in values)
        create_stmt = f"CREATE TYPE {enum_name} AS ENUM ({values_str})"
        conn.execute(create_stmt)
        logging.info(f"Created enum: {enum_name} with values: {values}")


def create_raw_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create raw schema for staging data.

    Args:
        conn: DuckDB connection object
    """
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    logging.info("Created raw schema")


def create_ref_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create ref schema for reference data.

    Args:
        conn: DuckDB connection object
    """
    conn.execute("CREATE SCHEMA IF NOT EXISTS ref")
    logging.info("Created ref schema")


def create_tables_from_config(
    conn: duckdb.DuckDBPyConnection,
    tables_config: List[Dict[str, Any]],
    table_prefix: str = "",
) -> None:
    """Create tables from configuration.

    Args:
        conn: DuckDB connection object
        tables_config: List of table configurations
        table_prefix: Optional prefix for table names (e.g., "raw")
    """
    for table in tables_config:
        try:
            name = table["name"]
            schema = table["schema"]
        except KeyError as e:
            logging.error(f"Missing required field in table config: {e}")
            continue

        # Build CREATE TABLE statement
        columns = []
        for col_name, col_def in schema.items():
            # Handle both string and dict formats
            if isinstance(col_def, dict):
                col_type = col_def["type"]
            else:
                col_type = col_def
            columns.append(f"{col_name} {col_type}")

        full_table_name = f"{table_prefix}.{name}" if table_prefix else name
        create_stmt = (
            f"CREATE TABLE IF NOT EXISTS {full_table_name} ({', '.join(columns)})"
        )

        try:
            conn.execute(create_stmt)
            logging.info(f"Created table: {full_table_name}")
        except Exception as e:
            logging.error(f"Error creating table {full_table_name}: {e}")


def create_metadata_table(
    conn: duckdb.DuckDBPyConnection, config: Dict[str, Any]
) -> None:
    """Create table metadata table and populate with descriptions from config.

    Args:
        conn: DuckDB connection object
        config: Configuration dictionary containing table definitions
    """
    # Create the metadata table with temporal characteristics
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS table_metadata (
            table_name VARCHAR PRIMARY KEY,
            schema_name VARCHAR,
            description TEXT,
            table_type VARCHAR,
            -- Temporal characteristics
            temporal_grain VARCHAR,  -- DAILY, WEEKLY, MONTHLY, QUARTERLY, EVENT_BASED, STATIC, SLOWLY_CHANGING, MIXED
            primary_date_column VARCHAR,  -- Which column to use for time joins
            has_revisions BOOLEAN DEFAULT FALSE,  -- Does data get revised?
            revision_start_column VARCHAR,  -- e.g., 'realtime_start'
            revision_end_column VARCHAR,    -- e.g., 'realtime_end'
            -- Partitioning
            partition_columns VARCHAR[],  -- Array of partition column names
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    logging.info("Created table_metadata table")

    # Insert raw table descriptions with temporal metadata
    if "raw_tables" in config:
        for table in config["raw_tables"]:
            name = table["name"]
            description = table.get("description", "").strip()

            # Extract temporal metadata from config
            temporal_grain = table.get("temporal_grain", "DAILY")
            primary_date_col = table.get("primary_date_column", "date")
            has_revisions = table.get("has_revisions", False)
            revision_start_col = table.get("revision_start_column")
            revision_end_col = table.get("revision_end_column")
            partition_cols = table.get("partition_by", [])

            conn.execute(
                """
                INSERT OR REPLACE INTO table_metadata 
                (table_name, schema_name, description, table_type, 
                 temporal_grain, primary_date_column, has_revisions, 
                 revision_start_column, revision_end_column, partition_columns)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    name,
                    "raw",
                    description,
                    "raw",
                    temporal_grain,
                    primary_date_col,
                    has_revisions,
                    revision_start_col,
                    revision_end_col,
                    partition_cols,
                ),
            )
            logging.info(f"Added metadata for raw.{name} (grain={temporal_grain})")

    # Insert reference table descriptions
    if "reference_tables" in config:
        for table in config["reference_tables"]:
            name = table["name"]
            description = table.get("description", "").strip()
            temporal_grain = table.get("temporal_grain", "STATIC")

            conn.execute(
                """
                INSERT OR REPLACE INTO table_metadata 
                (table_name, schema_name, description, table_type, temporal_grain)
                VALUES (?, ?, ?, ?, ?)
            """,
                (name, "ref", description, "reference", temporal_grain),
            )
            logging.info(f"Added metadata for ref.{name} (grain={temporal_grain})")


def create_column_metadata_table(
    conn: duckdb.DuckDBPyConnection, config: Dict[str, Any]
) -> None:
    """Create column metadata table for detailed column documentation.

    Args:
        conn: DuckDB connection object
        config: Configuration dictionary
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS column_metadata (
            table_name VARCHAR,
            schema_name VARCHAR,
            column_name VARCHAR,
            data_type VARCHAR,
            description TEXT,
            is_primary_date BOOLEAN DEFAULT FALSE,
            is_revision_timestamp BOOLEAN DEFAULT FALSE,
            is_system_metadata BOOLEAN DEFAULT FALSE,
            is_partition_key BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (schema_name, table_name, column_name)
        )
    """
    )
    logging.info("Created column_metadata table")

    # Populate from config - raw tables
    if "raw_tables" in config:
        for table in config["raw_tables"]:
            table_name = table["name"]
            schema_name = "raw"
            schema = table.get("schema", {})
            primary_date_col = table.get("primary_date_column", "date")
            revision_start_col = table.get("revision_start_column")
            revision_end_col = table.get("revision_end_column")
            partition_cols = table.get("partition_by", [])

            for col_name, col_def in schema.items():
                if isinstance(col_def, dict):
                    col_type = col_def["type"]
                    col_desc = col_def.get("description", "")
                else:
                    col_type = col_def
                    col_desc = ""

                is_primary_date = col_name == primary_date_col
                is_revision = col_name in [revision_start_col, revision_end_col]
                is_system = col_name.startswith("_")
                is_partition = col_name in partition_cols

                conn.execute(
                    """
                    INSERT OR REPLACE INTO column_metadata
                    (table_name, schema_name, column_name, data_type, description, 
                     is_primary_date, is_revision_timestamp, is_system_metadata, is_partition_key)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        table_name,
                        schema_name,
                        col_name,
                        col_type,
                        col_desc,
                        is_primary_date,
                        is_revision,
                        is_system,
                        is_partition,
                    ),
                )

            logging.info(
                f"Added column metadata for raw.{table_name} ({len(schema)} columns)"
            )

    # Populate from config - reference tables
    if "reference_tables" in config:
        for table in config["reference_tables"]:
            table_name = table["name"]
            schema_name = "ref"
            schema = table.get("schema", {})

            for col_name, col_def in schema.items():
                if isinstance(col_def, dict):
                    col_type = col_def["type"]
                    col_desc = col_def.get("description", "")
                else:
                    col_type = col_def
                    col_desc = ""

                is_system = col_name.startswith("_")

                conn.execute(
                    """
                    INSERT OR REPLACE INTO column_metadata
                    (table_name, schema_name, column_name, data_type, description, is_system_metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (table_name, schema_name, col_name, col_type, col_desc, is_system),
                )

            logging.info(
                f"Added column metadata for ref.{table_name} ({len(schema)} columns)"
            )


def load_reference_data_from_csv(
    conn: duckdb.DuckDBPyConnection, config: Dict[str, Any]
) -> None:
    """Load reference data from CSV files.

    Args:
        conn: DuckDB connection object
        config: Configuration dictionary containing paths
    """
    try:
        seeds_path = Path(config.get("seeds_path", "macrokit_datalake/seeds"))

        # Define CSV files to load
        csv_files = {
            "countries": "ref_countries.csv",
            "sources": "ref_sources.csv",
            "us_economic": "ref_us_economic.csv",
            "swap_conventions": "ref_swap_conventions.csv",
        }

        for table_name, csv_filename in csv_files.items():
            csv_path = seeds_path / csv_filename
            if csv_path.exists():
                try:
                    conn.execute(
                        f"""
                        INSERT INTO ref.{table_name} 
                        SELECT * FROM read_csv_auto('{csv_path}')
                    """
                    )
                    logging.info(f"Loaded reference data from {csv_path}")
                except Exception as e:
                    logging.warning(
                        f"Could not load {csv_filename} into ref.{table_name}: {e}"
                    )
            else:
                logging.warning(f"CSV file not found: {csv_path}")

    except Exception as e:
        logging.error(f"Error loading reference data: {e}")


def generate_date_dimension(
    conn: duckdb.DuckDBPyConnection,
    start_date: str = "2000-01-01",
    end_date: str = "2030-12-31",
) -> None:
    """Generate date dimension table.

    Args:
        conn: DuckDB connection object
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
    """
    logging.info(f"Generating date dimension from {start_date} to {end_date}")

    conn.execute(
        f"""
        INSERT INTO ref.date_dimension (
            date, year, quarter, month, day, day_of_week, day_name,
            is_business_day, is_month_end, is_quarter_end, is_year_end
        )
        WITH date_series AS (
            SELECT 
                date::DATE as date
            FROM generate_series(
                DATE '{start_date}',
                DATE '{end_date}',
                INTERVAL '1 day'
            ) AS t(date)
        )
        SELECT 
            date,
            EXTRACT(YEAR FROM date)::INTEGER as year,
            EXTRACT(QUARTER FROM date)::INTEGER as quarter,
            EXTRACT(MONTH FROM date)::INTEGER as month,
            EXTRACT(DAY FROM date)::INTEGER as day,
            EXTRACT(ISODOW FROM date)::INTEGER as day_of_week,
            CASE EXTRACT(ISODOW FROM date)
                WHEN 1 THEN 'Monday'
                WHEN 2 THEN 'Tuesday'
                WHEN 3 THEN 'Wednesday'
                WHEN 4 THEN 'Thursday'
                WHEN 5 THEN 'Friday'
                WHEN 6 THEN 'Saturday'
                WHEN 7 THEN 'Sunday'
            END as day_name,
            -- Simple business day logic (Mon-Fri, no holidays yet)
            EXTRACT(ISODOW FROM date) BETWEEN 1 AND 5 as is_business_day,
            date = LAST_DAY(date) as is_month_end,
            date = LAST_DAY(date) AND EXTRACT(MONTH FROM date) IN (3,6,9,12) as is_quarter_end,
            EXTRACT(MONTH FROM date) = 12 AND EXTRACT(DAY FROM date) = 31 as is_year_end
        FROM date_series
    """
    )

    # Update prior/next business day columns
    conn.execute(
        """
        UPDATE ref.date_dimension
        SET prior_business_day = (
            SELECT MAX(d2.date)
            FROM ref.date_dimension d2
            WHERE d2.is_business_day = TRUE
              AND d2.date < date_dimension.date
        ),
        next_business_day = (
            SELECT MIN(d2.date)
            FROM ref.date_dimension d2
            WHERE d2.is_business_day = TRUE
              AND d2.date > date_dimension.date
        )
    """
    )

    logging.info("Date dimension generated successfully")


def setup_parquet_storage(config: Dict[str, Any]) -> None:
    """Setup parquet storage directories.

    Args:
        config: Configuration dictionary containing storage settings

    Raises:
        KeyError: If storage configuration is missing
    """
    try:
        local_path = Path(config["storage"]["local_path"])
    except KeyError:
        raise KeyError("Storage local_path not found in configuration")

    local_path.mkdir(parents=True, exist_ok=True)

    logging.info(f"Created parquet storage at {local_path}")


def main(args: List[str]) -> None:
    """Main initialization function.

    Args:
        args: Command line arguments (unused)
    """
    logging.info("=" * 60)
    logging.info("MacroKit Data Lake Initialization (DBT-Ready)")
    logging.info("=" * 60)

    try:
        # Load configuration
        config = config_utils.load_config()

        # Create necessary folders
        create_folder_if_not_exists(config["storage"]["local_path"])

        # Create database
        conn = create_database(config)

        # Get enums from DBT and create them
        dbt_vars = get_enum_values_from_dbt()
        enum_values = map_dbt_vars_to_enums(dbt_vars)
        create_enums(conn, enum_values)

        # Always create raw schema and tables
        create_raw_schema(conn)
        if "raw_tables" in config:
            create_tables_from_config(conn, config["raw_tables"], "raw")

        # Create reference tables
        create_ref_schema(conn)
        if "reference_tables" in config:
            create_tables_from_config(conn, config["reference_tables"], "ref")

        # Create metadata tables (table-level and column-level)
        create_metadata_table(conn, config)
        create_column_metadata_table(conn, config)

        # Load reference data from CSV
        load_reference_data_from_csv(conn, config)

        # Generate date dimension
        generate_date_dimension(conn)

        # Setup parquet storage
        setup_parquet_storage(config)

        # Close connection
        conn.close()

        logging.info("=" * 60)
        logging.info("Data lake initialized successfully!")
        logging.info("")
        logging.info("Metadata available in:")
        logging.info("  - table_metadata (temporal grain, partitioning)")
        logging.info("  - column_metadata (column descriptions, flags)")
        logging.info("  - ref.date_dimension (calendar table)")
        logging.info("")
        logging.info("Next: Run ingest scripts then use DBT to build models")
        logging.info("=" * 60)

    except Exception as e:
        logging.error(f"Initialization failed: {e}")
        raise


if __name__ == "__main__":
    app.run(main)
