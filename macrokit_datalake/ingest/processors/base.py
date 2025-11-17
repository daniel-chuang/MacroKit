from abc import ABC, abstractmethod
from datetime import datetime
import pandas as pd
from absl import logging


class BaseProcessor(ABC):
    """Base class for all data processors"""

    def __init__(self, extractor, conn):
        self.extractor = extractor
        self.conn = conn

    @abstractmethod
    def get_series_config(self):
        """Return configuration for series to process"""
        pass

    @abstractmethod
    def get_table_name(self):
        """Return target table name"""
        pass

    @abstractmethod
    def transform_data(self, raw_data, series_info, **kwargs):
        """Transform raw data to standard format"""
        pass

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

        # Transform data
        df = self.transform_data(raw_data, series_info, series_id=series_id)
        if df is None or len(df) == 0:
            logging.warning(f"No data after transformation for {series_id}")
            return

        # Filter for updates if needed
        if update_only and not kwargs.get("force_full", False):
            df = self._filter_for_updates(df, series_info)
            if len(df) == 0:
                logging.info(f"No new data for {series_id}")
                return

        # Insert data
        self._insert_data(df)
        logging.info(f"✓ Inserted {len(df)} records for {series_id}")

    def _extract_data(self, series_id, start_date, end_date, **kwargs):
        """Extract data using the extractor"""
        return self.extractor.get_data(series_id, start_date, end_date, **kwargs)

    def _filter_for_updates(self, df, series_info):
        """Filter data for incremental updates - can be overridden"""
        # Default implementation - override in subclasses for specific logic
        return df

    def _insert_data(self, df):
        """Insert data into database"""
        table_name = self.get_table_name()

        # Get column names from DataFrame
        columns = ", ".join(df.columns)

        query = f"""
            INSERT INTO {table_name} ({columns})
            SELECT * FROM df
        """

        self.conn.execute(query)

    def add_common_columns(self, df, **kwargs):
        """Add common columns that most processors need"""
        df["_loaded_at"] = datetime.now()

        if "source" in kwargs:
            df["source"] = kwargs["source"]
        if "country" in kwargs:
            df["country"] = kwargs["country"]

        return df
