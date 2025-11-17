import pandas as pd
from datetime import datetime
from processors.base import BaseProcessor
from absl import logging


class MarketProcessor(BaseProcessor):
    """Process scalar market factors and regime indicators"""

    def get_config_file_name(self):
        """Return CSV filename for market data configuration"""
        return "ref_us_market_data.csv"

    def get_table_name(self):
        """Return table name"""
        return "raw.us_market_data"

    def _parse_config_df(self, df):
        """Custom parsing for market data configuration"""
        config = {}

        for _, row in df.iterrows():
            config[row["series_id"]] = {
                "indicator": row["indicator"],
                "asset_class": row["asset_class"],
                "maturity": row.get("maturity"),
            }

        return config

    def transform_data(self, raw_data, series_info, **kwargs):
        """Transform market data"""
        if raw_data is None or len(raw_data) == 0:
            return None

        df = raw_data.reset_index()
        df.columns = ["date", "value"]

        # Add series-specific info
        df["series_id"] = kwargs["series_id"]
        df["indicator"] = series_info["indicator"]
        df["asset_class"] = series_info["asset_class"]
        df["maturity"] = series_info.get("maturity")

        # Add common columns
        df = self.add_common_columns(df, source="FRED")

        # Type conversions
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

        # Drop NaN values
        df = df.dropna(subset=["value"])

        # Sort and reset index before returning
        df = df.sort_values("date").reset_index(drop=True)

        return df

    def _filter_for_updates(self, df, series_info):
        """Filter for market data updates - by series_id"""
        if len(df) == 0:
            return df

        series_id = df["series_id"].iloc[0]

        last_date = self.conn.execute(
            f"SELECT MAX(date) FROM {self.get_table_name()} WHERE series_id = ?",
            [series_id],
        ).fetchone()[0]

        if last_date:
            df = df[df["date"] > last_date].reset_index(drop=True)
            logging.info(f"Filtered to {len(df)} new observations after {last_date}")

        return df

    def _process_series(
        self, series_id, series_info, start_date, end_date, update_only, **kwargs
    ):
        """Override to add market-specific logging"""
        logging.info(
            f"Fetching market data for {series_info['indicator']} ({series_info['asset_class']})..."
        )

        super()._process_series(
            series_id, series_info, start_date, end_date, update_only, **kwargs
        )

        if hasattr(self, "_last_processed_df") and self._last_processed_df is not None:
            df = self._last_processed_df
            logging.info(f"  - {len(df)} observations")
            logging.info(f"  - Date range: {df['date'].min()} to {df['date'].max()}")
            if df["value"].notna().any():
                logging.info(
                    f"  - Value range: {df['value'].min():.2f} to {df['value'].max():.2f}"
                )

    def _insert_data(self, df):
        """Override to store df for statistics and insert"""
        self._last_processed_df = df
        super()._insert_data(df)
