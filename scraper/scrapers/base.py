import hashlib
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseScraper(ABC):
    @abstractmethod
    def search(self, query: str, location: str, date_hours: int = 24) -> List[Dict[str, Any]]:
        """
        Search for jobs matching query and location within date_hours.
        Returns a list of raw job data dicts.
        """
        pass

    @abstractmethod
    def normalize(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalizes raw job listings.
        Returns a list of dicts, each containing:
        - title
        - company
        - company_domain
        - location
        - experience_required
        - source
        - source_url
        - jd_text
        - posted_at (timezone aware datetime or None)
        - dedup_hash (auto-generated in this base class or child class)
        """
        pass

    def generate_dedup_hash(self, title: str, company: str, source: str) -> str:
        """
        Generates SHA256 of f"{title}{company}{source}".lower()
        """
        normalized_str = f"{title or ''}{company or ''}{source or ''}".strip().lower()
        return hashlib.sha256(normalized_str.encode('utf-8')).hexdigest()
