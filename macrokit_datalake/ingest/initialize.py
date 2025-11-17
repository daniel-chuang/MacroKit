import duckdb
import yaml
from pathlib import Path
from absl import logging
from absl import app
from absl import flags
import shutil
from typing import Dict, List, Any, Optional
import os

FLAGS = flags.FLAGS

flags.DEFINE_boolean("overwrite", False, "Whether to overwrite existing data")


def load_config(
    config_path: str = "macrokit_datalake/datalake_config.yaml",
) -> Dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to the configuration YAML file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is malformed
    """
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing configuration file: {e}")


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
        table_prefix: Optional prefix for table names (e.g., "raw.")
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

        # Load countries from CSV
        countries_csv = seeds_path / "ref_countries.csv"
        if countries_csv.exists():
            conn.execute(
                f"""
                INSERT INTO ref.countries 
                SELECT * FROM read_csv_auto('{countries_csv}')
            """
            )
            logging.info(f"Loaded reference countries from {countries_csv}")
        else:
            logging.warning(f"Countries CSV not found: {countries_csv}")

        # Load other reference data similarly
        sources_csv = seeds_path / "ref_sources.csv"
        if sources_csv.exists():
            conn.execute(
                f"""
                INSERT INTO ref.sources 
                SELECT * FROM read_csv_auto('{sources_csv}')
            """
            )
            logging.info(f"Loaded reference sources from {sources_csv}")

    except Exception as e:
        logging.error(f"Error loading reference data: {e}")


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
        config = load_config()

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
            # Load reference data
            load_reference_data_from_csv(conn, config)

        # Setup parquet storage
        setup_parquet_storage(config)

        # Close connection
        conn.close()

        logging.info("=" * 60)
        logging.info("Data lake initialized successfully!")
        logging.info("Next: Run ingest script then use DBT to build models")
        logging.info("=" * 60)

    except Exception as e:
        logging.error(f"Initialization failed: {e}")
        raise


if __name__ == "__main__":
    app.run(main)
