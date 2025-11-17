import pandas as pd
from datetime import datetime
from processors.base import BaseProcessor
from absl import logging


class EconomicProcessor(BaseProcessor):
    """Process economic indicator data with vintages"""

    def get_series_config(self):
        """Economic series configuration"""
        return {
            "GDP": {"indicator": "GDP", "frequency": "QUARTERLY", "unit": "BILLIONS"},
            "CPIAUCSL": {"indicator": "CPI", "frequency": "MONTHLY", "unit": "INDEX"},
            "UNRATE": {
                "indicator": "Unemployment Rate",
                "frequency": "MONTHLY",
                "unit": "PERCENT",
            },
        }

    def get_table_name(self):
        """Return table name"""
        return "raw.economic_indicators"

    def _extract_data(self, series_id, start_date, end_date, **kwargs):
        """Override to get vintage data"""
        return self.extractor.get_vintage_data(series_id)

    def transform_data(self, raw_data, series_info, **kwargs):
        """Transform economic data with vintages"""
        if raw_data is None or len(raw_data) == 0:
            return None

        # Convert vintage data to DataFrame
        df_all = raw_data.reset_index()

        logging.info(f"Retrieved {len(df_all)} total observations across all vintages")

        # Process vintages - minimal transformation, just type conversion
        all_records = []

        for _, row in df_all.iterrows():
            if pd.isna(row["value"]):
                continue

            # Handle missing realtime_end column
            realtime_end = row.get("realtime_end")
            if realtime_end is None or pd.isna(realtime_end):
                realtime_end = row["realtime_start"]

            record = {
                "series_id": kwargs["series_id"],
                "observation_date": pd.to_datetime(row["date"]).date(),
                "value": float(row["value"]),
                "realtime_start": pd.to_datetime(row["realtime_start"]).date(),
                "realtime_end": pd.to_datetime(realtime_end).date(),
                "indicator": series_info["indicator"],
                "unit": series_info["unit"],
                "frequency": series_info["frequency"],
            }
            all_records.append(record)

        if not all_records:
            return None

        df = pd.DataFrame(all_records)
        df = self.add_common_columns(df, source="FRED", country="US")

        return df.sort_values(["observation_date", "realtime_start"])

    def _process_series(
        self, series_id, series_info, start_date, end_date, update_only, **kwargs
    ):
        """Override to add economic-specific logging"""
        logging.info(f"Fetching vintage data for {series_info['indicator']}...")

        # Call parent method
        super()._process_series(
            series_id, series_info, start_date, end_date, update_only, **kwargs
        )

        # Add economic-specific statistics logging
        if hasattr(self, "_last_processed_df") and self._last_processed_df is not None:
            df = self._last_processed_df
            num_observations = len(df)
            num_unique_dates = df["observation_date"].nunique()
            num_vintages = df.groupby("observation_date")["realtime_start"].count()
            num_revised = (num_vintages > 1).sum()
            avg_vintages = (
                num_observations / num_unique_dates if num_unique_dates > 0 else 0
            )

            logging.info(f"  - {num_unique_dates} unique observation dates")
            logging.info(
                f"  - {num_revised} dates with revisions ({num_revised/num_unique_dates*100:.1f}%)"
            )
            logging.info(f"  - {avg_vintages:.1f} avg vintages per date")

    def _insert_data(self, df):
        """Override to store df for statistics and insert"""
        self._last_processed_df = df
        super()._insert_data(df)
