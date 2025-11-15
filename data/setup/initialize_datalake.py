import duckdb
import yaml
from pathlib import Path
from absl import logging
from absl import app
from absl import flags
import shutil

FLAGS = flags.FLAGS

flags.DEFINE_boolean("overwrite", False, "Whether to overwrite existing data")


def load_config(config_path="config/database/datalake_config.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def create_folder_if_not_exists(folder_path):
    # Overwrite existing folder if flag is set
    if FLAGS.overwrite and Path(folder_path).exists():
        logging.info(f"Overwriting existing folder: {folder_path}")
        shutil.rmtree(folder_path)
    else:
        logging.info(f"Creating folder: {folder_path}")
    Path(folder_path).mkdir(parents=True, exist_ok=True)


def create_database(config):
    db_path = config["database"]["path"]

    # Remove existing database if overwrite flag is set
    if FLAGS.overwrite and Path(db_path).exists():
        logging.info(f"Overwriting existing database: {db_path}")
        Path(db_path).unlink()

    conn = duckdb.connect(db_path)
    logging.info(f"Created DuckDB database at {db_path}")
    return conn


def create_enums(conn, config):
    if not config["database"]["enums"]:
        raise ValueError("No enums defined in configuration.")

    for enum_name, enum_values in config["database"]["enums"].items():
        result = conn.execute(
            f"SELECT 1 FROM duckdb_types() WHERE type_name = '{enum_name}'"
        ).fetchone()
        if result:
            logging.info(f"Enum {enum_name} already exists, skipping")
            continue

        values_str = ", ".join(f"'{v}'" for v in enum_values)
        create_stmt = f"CREATE TYPE {enum_name} AS ENUM ({values_str})"
        conn.execute(create_stmt)
        logging.info(f"Created enum: {enum_name}")


def create_tables(conn, config):
    for table in config["tables"]:
        name = table["name"]
        schema = table["schema"]

        # Build CREATE TABLE statement
        columns = []
        for col_name, col_type in schema.items():
            columns.append(f"{col_name} {col_type}")

        create_stmt = f"CREATE TABLE IF NOT EXISTS {name} ({', '.join(columns)})"
        conn.execute(create_stmt)

        logging.info(f"Created table: {name}")


def setup_parquet_storage(config):
    local_path = Path(config["storage"]["local_path"])
    local_path.mkdir(parents=True, exist_ok=True)

    logging.info(f"Created parquet storage at {local_path}")


def main(args):
    logging.info("=" * 60)
    logging.info("MacroKit Data Lake Initialization")
    logging.info("=" * 60)

    # Load configuration
    config = load_config()

    # Create necessary folders
    create_folder_if_not_exists(config["storage"]["local_path"])

    # Create database
    conn = create_database(config)

    # Create enums
    create_enums(conn, config)

    # Create tables
    create_tables(conn, config)

    # Setup parquet storage
    setup_parquet_storage(config)

    # Close connection
    conn.close()

    logging.info("\n" + "=" * 60)
    logging.info("Data lake initialized successfully!")
    logging.info("=" * 60)
    logging.info("\nNext steps:")
    logging.info("1. Run the data ingestion script to populate tables")
    logging.info("2. Set up VM mount for parquet files (if using VM)")
    logging.info("3. Configure data update schedule")


if __name__ == "__main__":
    app.run(main)
