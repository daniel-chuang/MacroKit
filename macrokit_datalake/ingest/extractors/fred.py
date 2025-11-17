from fredapi import Fred
from extractors.base import BaseExtractor
from absl import logging


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

    def get_vintage_data(self, series_id, **kwargs):
        """Get all vintage data for a series"""
        return self.client.get_series_all_releases(series_id)
