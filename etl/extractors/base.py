from abc import ABC, abstractmethod
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    def __init__(self, source_conn):
        self.source_conn = source_conn

    @abstractmethod
    def extract(self, table_name, last_sync=None):
        pass
