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


class ApifyNaukriScraper(BaseScraper):
    ACTOR_ID = "logiover/naukri-job-scraper"

    def search(self, query: str, location: str, date_hours: int = 24) -> List[Dict[str, Any]]:
        api_key = os.environ.get("APIFY_API_KEY")
        if not api_key:
            logger.error("APIFY_API_KEY not found in environment")
            return []

        client = ApifyClient(api_key)
        try:
            logger.info(f"[ApifyNaukri] Calling actor '{self.ACTOR_ID}' for '{query}' in '{location}'")
            run = client.actor(self.ACTOR_ID).call(run_input={
                "keyword": query,
                "location": location,
                "maxResults": 50,
                "maxItems": 50,
            })
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            logger.info(f"[ApifyNaukri] Got {len(items)} raw items from Apify")
            return self.normalize(items)
        except Exception as e:
            logger.error(f"[ApifyNaukri] Error calling Apify actor '{self.ACTOR_ID}': {e}")
            return []

    def normalize(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for item in items:
            # logiover actor field names (with fallbacks for schema variations)
            title = (
                item.get("title") or
                item.get("jobTitle") or
                item.get("job_title") or
                ""
            ).strip()

            source_url = (
                item.get("url") or
                item.get("jobUrl") or
                item.get("job_url") or
                item.get("link") or
                ""
            ).strip()

            if not title or not source_url:
                continue

            company = (
                item.get("company") or
                item.get("companyName") or
                item.get("company_name") or
                ""
            ).strip()

            location_str = (
                item.get("location") or
                item.get("jobLocation") or
                ""
            ).strip()

            experience = (
                item.get("experience") or
                item.get("experienceRequired") or
                item.get("exp") or
                ""
            ).strip()

            jd_text = (
                item.get("description") or
                item.get("jobDescription") or
                item.get("job_description") or
                item.get("details") or
                ""
            ).strip()

            # Extract company domain
            company_domain = ""
            website = (
                item.get("companyWebsite") or
                item.get("company_website") or
                item.get("website") or
                ""
            )
            if website:
                try:
                    parsed = urlparse(website)
                    company_domain = parsed.netloc.replace("www.", "").strip()
                except Exception:
                    pass

            if not company_domain and company:
                clean = re.sub(r'[^a-z0-9]', '', company.lower())
                company_domain = f"{clean}.com" if clean else ""

            # Parse posted_at
            posted_str = (
                item.get("posted") or
                item.get("postedDate") or
                item.get("posted_date") or
                item.get("postDate") or
                ""
            )
            posted_at = timezone.now()
            if posted_str:
                posted_lower = str(posted_str).lower()
                if any(w in posted_lower for w in ["today", "just now", "hour", "minute"]):
                    posted_at = timezone.now()
                elif "yesterday" in posted_lower:
                    posted_at = timezone.now() - timezone.timedelta(days=1)
                else:
                    days_match = re.search(r'(\d+)\s*days?\s*ago', posted_lower)
                    if days_match:
                        posted_at = timezone.now() - timezone.timedelta(days=int(days_match.group(1)))
                    else:
                        try:
                            parsed_date = parse_date(str(posted_str))
                            posted_at = (
                                timezone.make_aware(parsed_date)
                                if timezone.is_naive(parsed_date)
                                else parsed_date
                            )
                        except Exception:
                            pass

            source = "naukri"
            dedup_hash = hashlib.sha256(
                f"{title.lower()}{company.lower()}naukri".encode('utf-8')
            ).hexdigest()

            normalized.append({
                "title": title,
                "company": company,
                "company_domain": company_domain,
                "location": location_str,
                "experience_required": experience,
                "source": source,
                "source_url": source_url,
                "jd_text": jd_text,
                "posted_at": posted_at,
                "dedup_hash": dedup_hash,
            })

        logger.info(f"[ApifyNaukri] Normalized {len(normalized)} valid jobs")
        return normalized
