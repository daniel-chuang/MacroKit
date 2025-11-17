import pandas as pd
from datetime import datetime
from processors.base import BaseProcessor
from absl import logging


class TreasuryYieldProcessor(BaseProcessor):
    """Process Treasury Constant Maturity (CMT) yield curves"""

    def get_config_file_name(self):
        """Return CSV filename for treasury yields configuration"""
        return "ref_us_treasury_yields.csv"

    def get_table_name(self):
        """Return table name"""
        return "raw.us_treasury_yields"

    def _parse_config_df(self, df):
        """Custom parsing for treasury yield configuration"""
        config = {}

        for _, row in df.iterrows():
            config[row["series_id"]] = {
                "indicator": row["indicator"],
                "tenor": row["tenor"],
                "curve_type": row["curve_type"],
            }

        return config

    def transform_data(self, raw_data, series_info, **kwargs):
        """Transform Treasury yield data for curve structure"""
        if raw_data is None or len(raw_data) == 0:
            return None

        df = raw_data.reset_index()
        df.columns = ["date", "yield"]

        # Add series-specific info
        df["series_id"] = kwargs["series_id"]
        df["tenor"] = series_info["tenor"]
        df["curve_type"] = series_info["curve_type"]
        df["indicator"] = series_info["indicator"]

        # Type conversions first
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["yield"] = pd.to_numeric(df["yield"], errors="coerce")

        # Drop NaN yields and reset index immediately
        # df = df.dropna(subset=["yield"]).reset_index(drop=True)

        if len(df) == 0:
            return None

        # Convert from percentage to decimal (4.23% to 0.0423)
        df["yield"] = df["yield"] / 100.0

        # Add bid/ask placeholders
        df["bid"] = None
        df["ask"] = None

        # Add common columns
        df = self.add_common_columns(df, source="FRED")

        # Final sort and return with fresh index
        df = df.sort_values(["date", "tenor"]).reset_index(drop=True)

        return df

    def _filter_for_updates(self, df, series_info):
        """Filter for Treasury yield updates - by tenor and curve_type"""
        if len(df) == 0:
            return df

        # Use .iloc[0] for safe index access after potential filtering operations
        tenor = df["tenor"].iloc[0]
        curve_type = df["curve_type"].iloc[0]

        last_date = self.conn.execute(
            f"""
            SELECT MAX(date) 
            FROM {self.get_table_name()} 
            WHERE tenor = ? AND curve_type = ?
            """,
            [tenor, curve_type],
        ).fetchone()[0]

        if last_date:
            df = df[df["date"] > last_date].reset_index(drop=True)
            logging.info(
                f"Filtered to {len(df)} new observations after {last_date} for {tenor} {curve_type}"
            )

        return df

    def _process_series(
        self, series_id, series_info, start_date, end_date, update_only, **kwargs
    ):
        """Override to add Treasury-specific logging"""
        logging.info(
            f"Fetching Treasury CMT for {series_info['tenor']} ({series_info['indicator']})..."
        )

        super()._process_series(
            series_id, series_info, start_date, end_date, update_only, **kwargs
        )

        if hasattr(self, "_last_processed_df") and self._last_processed_df is not None:
            df = self._last_processed_df
            logging.info(f"  - {len(df)} observations")
            logging.info(f"  - Date range: {df['date'].min()} to {df['date'].max()}")
            if df["yield"].notna().any():
                logging.info(
                    f"  - Yield range: {df['yield'].min()*100:.2f}% to {df['yield'].max()*100:.2f}%"
                )

    def _insert_data(self, df):
        """Override to store df for statistics and insert"""
        self._last_processed_df = df
        super()._insert_data(df)
