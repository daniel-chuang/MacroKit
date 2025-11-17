"""Base class for data extractors"""

from abc import ABC, abstractmethod
from datetime import datetime


class BaseExtractor(ABC):
    """Base class for all data extractors"""

    def __init__(self, api_key=None):
        self.api_key = api_key
        self._client = None

    @abstractmethod
    def connect(self):
        """Initialize API client"""
        pass

    @abstractmethod
    def get_data(self, series_id, start_date, end_date, **kwargs):
        """Extract data for a given series"""
        pass

    @property
    def client(self):
        """Lazy load API client"""
        if self._client is None:
            self._client = self.connect()
        return self._client
