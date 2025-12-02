from fredapi import Fred
from extractors.base import BaseExtractor
from absl import logging
import pandas as pd


class FREDExtractor(BaseExtractor):
    """FRED API data extractor"""

    def connect(self):
        """Initialize FRED client"""
        if not self.api_key:
            raise ValueError("FRED_API_KEY is required")
        return Fred(api_key=self.api_key)

    def get_data(self, series_id, start_date, end_date, **kwargs):
        """Get series data from FRED"""
        return self.client.get_series(
            series_id, observation_start=start_date, observation_end=end_date
        )

    def get_vintage_data(self, series_id, start_date=None, end_date=None, **kwargs):
        """Get all vintage data for a series"""
        if not end_date:
            series = self.client.get_series_all_releases(series_id)
            series.index = pd.to_datetime(series.index)
        else:
            series = self.client.get_series_as_of_date(series_id, as_of_date=end_date)
            series.index = pd.to_datetime(series.index)
            end_date = pd.to_datetime(end_date)
            series = series[series.index <= end_date]

        if start_date:
            start_date = pd.to_datetime(start_date)
            series = series[series.index >= start_date]

        return series
