from abc import ABC, abstractmethod
from datetime import datetime
import pandas as pd
from absl import logging
import os


class BaseProcessor(ABC):
    """Base class for all data processors"""

    def __init__(self, extractor, conn):
        self.extractor = extractor
        self.conn = conn
        self._series_config = None

    @abstractmethod
    def get_config_file_name(self):
        """Return the CSV filename for this processor's configuration"""
        pass

    @abstractmethod
    def get_table_name(self):
        """Return target table name"""
        pass

    @abstractmethod
    def transform_data(self, raw_data, series_info, **kwargs):
        """Transform raw data to standard format"""
        pass

    def get_series_config(self):
        """Load series configuration from CSV"""
        if self._series_config is None:
            # Path to the seeds directory
            config_file = self.get_config_file_name()
            seeds_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "seeds",
                config_file,
            )

            try:
                df = pd.read_csv(seeds_path)

                # Filter to only active series if 'active' column exists
                if "active" in df.columns:
                    df = df[df["active"] == True]

                # Convert to dictionary format
                self._series_config = self._parse_config_df(df)

                logging.info(
                    f"Loaded {len(self._series_config)} series from {config_file}"
                )

            except FileNotFoundError:
                logging.error(f"Configuration CSV not found at {seeds_path}")
                self._series_config = {}
            except Exception as e:
                logging.error(f"Error loading configuration CSV: {e}")
                self._series_config = {}

        return self._series_config

    def _parse_config_df(self, df):
        """
        Parse configuration DataFrame into dictionary format.
        Override this in subclasses to customize parsing logic.

        Default implementation: assumes 'series_id' column exists and all other
        columns become the series_info dictionary.
        """
        config = {}

        if "series_id" not in df.columns:
            logging.error("Configuration CSV must have 'series_id' column")
            return config

        for _, row in df.iterrows():
            series_id = row["series_id"]
            # Convert row to dict, excluding series_id
            series_info = row.drop("series_id").to_dict()
            config[series_id] = series_info

        return config

    def process(self, start_date, end_date, update_only=False, **kwargs):
        """Main processing method - template pattern"""
        series_config = self.get_series_config()
        table_name = self.get_table_name()
        logging.info(f"Processing {len(series_config)} series for {table_name}")

        for series_id, series_info in series_config.items():
            try:
                self._process_series(
                    series_id, series_info, start_date, end_date, update_only, **kwargs
                )
            except Exception as e:
                logging.error(f"Error processing {series_id}: {e}")
                if kwargs.get("raise_on_error", False):
                    raise

    def _process_series(
        self, series_id, series_info, start_date, end_date, update_only, **kwargs
    ):
        """Process a single series"""
        # Extract data
        raw_data = self._extract_data(series_id, start_date, end_date, **kwargs)
        if raw_data is None or len(raw_data) == 0:
            logging.warning(f"No data extracted for {series_id}")
            return
        logging.info("✓ Extracted data for {series_id}")

        # Transform data
        df = self.transform_data(raw_data, series_info, series_id=series_id)
        if df is None or len(df) == 0:
            logging.warning(f"No data after transformation for {series_id}")
            return
        logging.info(f"✓ Transformed data for {series_id}")

        # Filter for updates if needed
        if update_only and not kwargs.get("force_full", False):
            df = self._filter_for_updates(df, series_info)
            if len(df) == 0:
                logging.info(f"No new data for {series_id}")
                return
        logging.info(f"✓ Filtered data for updates for {series_id}")

        # Insert data
        self._insert_data(df)
        logging.info(f"✓ Inserted {len(df)} records for {series_id}")

    def _extract_data(self, series_id, start_date, end_date, **kwargs):
        """Extract data using the extractor"""
        return self.extractor.get_data(series_id, start_date, end_date, **kwargs)

    def _filter_for_updates(self, df, series_info):
        """Filter data for incremental updates - can be overridden"""
        # Default implementation - override in subclasses for specific logic
        # Ensure we have a clean index before returning
        return df.reset_index(drop=True)

    def _insert_data(self, df):
        """Insert data into database"""
        table_name = self.get_table_name()

        # Ensure DataFrame has a clean integer index starting from 0
        df = df.reset_index(drop=True)

        # Use DuckDB's INSERT FROM VALUES with explicit column mapping
        columns = list(df.columns)
        column_str = ", ".join(columns)

        # Convert DataFrame to list of tuples for insertion
        values = [tuple(row) for row in df.itertuples(index=False, name=None)]

        # Create placeholders for parameterized query
        placeholder = "(" + ", ".join(["?" for _ in columns]) + ")"
        values_str = ", ".join([placeholder for _ in range(len(values))])

        query = f"INSERT INTO {table_name} ({column_str}) VALUES {values_str}"

        # Flatten the values list for the parameterized query
        flat_values = [item for sublist in values for item in sublist]

        self.conn.execute(query, flat_values)

    def add_common_columns(self, df, **kwargs):
        """Add common columns that most processors need"""
        df["_loaded_at"] = datetime.now()
        if "source" in kwargs:
            df["source"] = kwargs["source"]
        if "country" in kwargs:
            df["country"] = kwargs["country"]
        return df
