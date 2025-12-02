import pandas as pd
from datetime import datetime
from processors.base import BaseProcessor
from absl import logging


class EconomicProcessor(BaseProcessor):
    """Process economic indicator data with vintages"""

    def get_config_file_name(self):
        """Return CSV filename for economic series configuration"""
        return "ref_us_economic.csv"

    def get_table_name(self):
        """Return table name"""
        return "raw.us_economic_indicators"

    def _parse_config_df(self, df):
        """Custom parsing for economic series configuration"""
        config = {}

        for _, row in df.iterrows():
            config[row["series_id"]] = {
                "indicator": row["indicator"],
                "frequency": row["frequency"],
                "unit": row["unit"],
                "category": row["category"],
                "subcategory": row["subcategory"],
            }

        return config

    def _extract_data(self, series_id, start_date, end_date, **kwargs):
        """Override to get vintage data"""
        return self.extractor.get_vintage_data(
            series_id, start_date, end_date, **kwargs
        )

    def transform_data(self, raw_data, series_info, **kwargs):
        """Transform economic data with vintages"""
        if raw_data is None or len(raw_data) == 0:
            return None

        # Convert vintage data to DataFrame
        if isinstance(raw_data, pd.Series):
            df_all = raw_data.to_frame(name="value").reset_index()
        elif isinstance(raw_data, pd.DataFrame):
            df_all = raw_data.reset_index()
        else:
            logging.error("Raw data is not a pandas Series or DataFrame.")
            return None

        logging.info(f"Retrieved {len(df_all)} total observations across all vintages")

        # Assign series_id and indicator info
        df_all["series_id"] = kwargs["series_id"]
        df_all["indicator"] = series_info["indicator"]
        df_all["unit"] = series_info["unit"]
        df_all["category"] = series_info["category"]
        df_all["subcategory"] = series_info["subcategory"]
        df_all["frequency"] = series_info["frequency"]

        # Rename and convert date columns
        df_all = df_all.rename(columns={"date": "observation_date"})
        df_all["observation_date"] = pd.to_datetime(df_all["observation_date"]).dt.date

        # Handle realtime_start column
        if "realtime_start" in df_all.columns:
            df_all["realtime_start"] = pd.to_datetime(df_all["realtime_start"]).dt.date
        else:
            df_all["realtime_start"] = df_all["observation_date"]

        # Handle realtime_end column
        if "realtime_end" not in df_all.columns:
            df_all["realtime_end"] = df_all["realtime_start"]
        else:
            df_all["realtime_end"] = pd.to_datetime(df_all["realtime_end"]).dt.date
            mask = df_all["realtime_end"].isna()
            df_all.loc[mask, "realtime_end"] = df_all.loc[mask, "realtime_start"]

        # Convert value column
        df_all["value"] = pd.to_numeric(df_all["value"], errors="coerce")

        # Drop NaN values
        df_all = df_all.dropna(subset=["value"])

        if df_all.empty:
            return None

        # Select and order final columns
        df = df_all[
            [
                "series_id",
                "category",
                "subcategory",
                "observation_date",
                "value",
                "realtime_start",
                "realtime_end",
                "indicator",
                "unit",
                "frequency",
            ]
        ]

        df = self.add_common_columns(df, source="FRED")

        # Sort and reset index before returning
        df = df.sort_values(by=["observation_date", "realtime_start"]).reset_index(
            drop=True
        )

        return df

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
            num_vintages_per_date = df.groupby("observation_date")[
                "realtime_start"
            ].nunique()
            num_revised = (num_vintages_per_date > 1).sum()
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
