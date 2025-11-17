import pandas as pd
from datetime import datetime
from processors.base import BaseProcessor


class TreasuryProcessor(BaseProcessor):
    """Process treasury yield data"""

    def get_series_config(self):
        """Treasury series configuration"""
        return {
            "DGS1MO": {"maturity": "1M"},
            "DGS3MO": {"maturity": "3M"},
            "DGS6MO": {"maturity": "6M"},
            "DGS1": {"maturity": "1Y"},
            "DGS2": {"maturity": "2Y"},
            "DGS3": {"maturity": "3Y"},
            "DGS5": {"maturity": "5Y"},
            "DGS7": {"maturity": "7Y"},
            "DGS10": {"maturity": "10Y"},
            "DGS20": {"maturity": "20Y"},
            "DGS30": {"maturity": "30Y"},
        }

    def get_table_name(self):
        """Return table name"""
        return "raw.treasury_yields"

    def transform_data(self, raw_data, series_info, **kwargs):
        """Transform treasury data"""
        df = raw_data.reset_index()
        df.columns = ["date", "yield"]

        # Add series-specific info
        df["maturity"] = series_info["maturity"]
        df["series_id"] = kwargs["series_id"]

        # Add common columns
        df = self.add_common_columns(df, source="FRED", country="US")

        # Type conversions
        df["date"] = pd.to_datetime(df["date"]).dt.date

        return df

    def _filter_for_updates(self, df, series_info):
        """Filter for treasury-specific updates"""
        maturity = series_info["maturity"]

        last_date = self.conn.execute(
            "SELECT MAX(date) FROM raw.treasury_yields WHERE maturity = ? AND country = ?",
            [maturity, "US"],
        ).fetchone()[0]

        if last_date:
            df = df[df["date"] > last_date]

        return df
