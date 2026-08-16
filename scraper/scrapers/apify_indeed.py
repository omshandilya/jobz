import hashlib
import os
import re
from typing import List, Dict, Any
from urllib.parse import urlparse
from dateutil.parser import parse as parse_date
from django.utils import timezone
from apify_client import ApifyClient
from .base import BaseScraper
import logging

logger = logging.getLogger(__name__)

class ApifyIndeedScraper(BaseScraper):
    def search(self, query: str, location: str, date_hours: int = 24) -> List[Dict[str, Any]]:
        api_key = os.environ.get("APIFY_API_KEY")
        if not api_key:
            logger.error("APIFY_API_KEY not found in environment")
            return []

        client = ApifyClient(api_key)
        try:
            run = client.actor("misceres/indeed-scraper").call(run_input={
                "query": query,
                "location": location + ", India",
                "maxItems": 50,
                "country": "IN"
            })
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            return self.normalize(items)
        except Exception as e:
            logger.error(f"Error calling Apify Indeed scraper: {e}")
            return []

    def normalize(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for item in items:
            title = item.get("positionName", "")
            source_url = item.get("url", "")
            
            if not title or not source_url:
                continue

            company = item.get("company", "")
            
            company_domain = ""
            company_url = item.get("companyUrl", "")
            if company_url:
                try:
                    parsed = urlparse(company_url)
                    company_domain = parsed.netloc.replace("www.", "").strip()
                except Exception:
                    pass

            if not company_domain and company:
                clean = re.sub(r'[^a-z0-9]', '', company.lower())
                company_domain = f"{clean}.com" if clean else ""

            posted_str = item.get("postedAt", "")
            posted_at = timezone.now()
            if posted_str:
                try:
                    if isinstance(posted_str, int):
                        # Timestamp in milliseconds
                        posted_at = timezone.datetime.fromtimestamp(posted_str / 1000.0, tz=timezone.utc)
                    else:
                        s = str(posted_str).lower().strip()
                        if any(w in s for w in ["today", "just now", "hour", "minute"]):
                            posted_at = timezone.now()
                        elif "yesterday" in s:
                            posted_at = timezone.now() - timezone.timedelta(days=1)
                        else:
                            # "N days ago" or "30+ days ago"
                            days_match = re.search(r'(\d+)\+?\s*days?\s*ago', s)
                            if days_match:
                                posted_at = timezone.now() - timezone.timedelta(days=int(days_match.group(1)))
                            else:
                                parsed_date = parse_date(str(posted_str))
                                posted_at = (
                                    timezone.make_aware(parsed_date)
                                    if timezone.is_naive(parsed_date)
                                    else parsed_date
                                )
                except Exception:
                    logger.debug(f"Could not parse date: {posted_str}")


            source = "indeed"
            raw_dedup_str = f"{title.lower()}{company.lower()}indeed"
            dedup_hash = hashlib.sha256(raw_dedup_str.encode('utf-8')).hexdigest()

            normalized.append({
                "title": title,
                "company": company,
                "company_domain": company_domain,
                "location": item.get("location", ""),
                "experience_required": "",
                "source": source,
                "source_url": source_url,
                "jd_text": item.get("description", ""),
                "posted_at": posted_at,
                "dedup_hash": dedup_hash
            })
        return normalized
