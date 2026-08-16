import time
import random
import re
import logging
import hashlib
from typing import List, Dict, Any
from urllib.parse import urlparse
from django.utils import timezone
from playwright.sync_api import sync_playwright
from .base import BaseScraper

logger = logging.getLogger(__name__)

# playwright-stealth is optional — apply if available
try:
    from playwright_stealth import stealth_sync
    _STEALTH_AVAILABLE = True
except ImportError:
    try:
        from playwright_stealth import Stealth
        def stealth_sync(page):
            Stealth().apply_stealth_sync(page)
        _STEALTH_AVAILABLE = True
    except ImportError:
        _STEALTH_AVAILABLE = False
        logger.warning("playwright-stealth not installed. Bot detection risk is higher.")

class IndeedScraper(BaseScraper):
    def search(self, query: str, location: str, date_hours: int = 24) -> List[Dict[str, Any]]:
        # Format query and location for URL
        q = re.sub(r'\s+', '+', query.strip())
        l = re.sub(r'\s+', '+', location.strip())
        
        # Indeed India base URL
        url_base = f"https://in.indeed.com/jobs?q={q}&l={l}&fromage=1"
        logger.info(f"IndeedScraper: searching URL: {url_base}")

        raw_jobs = []

        with sync_playwright() as p:
            # Use Chromium with stealth to avoid Cloudflare bot protection
            browser = None
            try:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"]
                )
            except Exception as launch_err:
                logger.error(f"Failed to launch browser for Indeed: {launch_err}")
                return []

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()

            if _STEALTH_AVAILABLE:
                stealth_sync(page)
                logger.info("IndeedScraper: playwright-stealth applied.")

            try:
                # Max 2 pages
                for page_num in range(1, 3):
                    page_url = url_base if page_num == 1 else f"{url_base}&start={(page_num - 1) * 10}"
                    logger.info(f"Scraping Indeed page {page_num}: {page_url}")

                    resp = page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(random.uniform(3.0, 6.0))

                    # Random scrolling to mimic human
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3);")
                    time.sleep(1.0)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
                    time.sleep(1.0)

                    # Cloudflare block check
                    if page.query_selector("div.cf-turnstile") or "cloudflare" in page.title().lower():
                        logger.warning(f"Cloudflare Turnstile block detected on page {page_num}!")
                        break

                    # Wait for job cards
                    try:
                        page.wait_for_selector(".job_seen_beacon", timeout=10000)
                    except Exception:
                        logger.warning(f"No job cards appeared on Indeed page {page_num}.")
                        break

                    job_elements = page.query_selector_all(".job_seen_beacon")
                    if not job_elements:
                        break
                    
                    logger.info(f"Found {len(job_elements)} jobs on Indeed page {page_num}")

                    for el in job_elements:
                        try:
                            # Title & URL
                            title_el = el.query_selector(".jobTitle span[title], .jobTitle a span, .jobTitle")
                            title = title_el.inner_text().strip() if title_el else ""

                            url_el = el.query_selector(".jobTitle a")
                            job_url = url_el.get_attribute("href") if url_el else ""
                            if job_url and not job_url.startswith("http"):
                                # If it's a relative indeed link, prefix it
                                job_url = "https://in.indeed.com" + job_url
                            
                            # Company
                            company_el = el.query_selector("[data-testid='company-name']")
                            company = company_el.inner_text().strip() if company_el else ""

                            # Location
                            loc_el = el.query_selector("[data-testid='text-location']")
                            job_loc = loc_el.inner_text().strip() if loc_el else location

                            if title and job_url:
                                raw_jobs.append({
                                    "title": title,
                                    "company": company,
                                    "location": job_loc,
                                    "experience_required": "",
                                    "source_url": job_url,
                                    "posted_str": "today", # hardcoded 1 day based on URL fromage=1
                                })
                        except Exception as e:
                            logger.error(f"Error parsing Indeed job card: {e}")
            except Exception as e:
                logger.error(f"Error scraping Indeed search results: {e}")

            # Visit each job detail URL to extract full JD text
            for raw_job in raw_jobs[:10]:
                try:
                    time.sleep(random.uniform(2.5, 4.5))
                    page.goto(raw_job["source_url"], wait_until="domcontentloaded", timeout=25000)
                    time.sleep(random.uniform(1.5, 2.5))

                    jd_el = page.query_selector("#jobDescriptionText")
                    jd_text = jd_el.inner_text().strip() if jd_el else ""
                    if not jd_text:
                        jd_text = page.evaluate("() => document.body.innerText")[:2000]
                    raw_job["jd_text"] = jd_text

                    # Extract company domain logic
                    company_domain = ""
                    try:
                        all_links = page.query_selector_all("a[href]")
                        for link in all_links:
                            try:
                                href = link.get_attribute("href") or ""
                                text = link.inner_text().strip().lower()
                                if (
                                    href.startswith("http")
                                    and "indeed.com" not in href
                                    and any(w in text for w in ["website", "company", "www", "homepage"])
                                ):
                                    parsed = urlparse(href)
                                    netloc = parsed.netloc.replace("www.", "").strip()
                                    if netloc:
                                        company_domain = netloc
                                        break
                            except Exception:
                                continue
                    except Exception:
                        pass

                    if not company_domain and raw_job.get("company"):
                        clean = re.sub(r'[^a-z0-9]', '', raw_job["company"].lower())
                        company_domain = f"{clean}.com" if clean else ""
                    
                    raw_job["company_domain"] = company_domain

                except Exception as e:
                    logger.error(f"Error fetching Indeed JD from {raw_job['source_url']}: {e}")
                    raw_job["jd_text"] = "Job description extraction failed."
                    clean = re.sub(r'[^a-z0-9]', '', raw_job.get("company", "").lower())
                    raw_job["company_domain"] = f"{clean}.com" if clean else ""

            browser.close()

        return self.normalize(raw_jobs)

    def normalize(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for raw in raw_jobs:
            posted_at = timezone.now()
            
            title = raw.get("title", "")
            company = raw.get("company", "")
            source = "indeed"

            raw_dedup_str = f"{title.lower()}{company.lower()}indeed"
            dedup_hash = hashlib.sha256(raw_dedup_str.encode('utf-8')).hexdigest()

            normalized.append({
                "title": title,
                "company": company,
                "company_domain": raw.get("company_domain", ""),
                "location": raw.get("location", ""),
                "experience_required": raw.get("experience_required", ""),
                "source": source,
                "source_url": raw.get("source_url", ""),
                "jd_text": raw.get("jd_text", "Job description extraction failed."),
                "posted_at": posted_at,
                "dedup_hash": dedup_hash,
            })
        return normalized
