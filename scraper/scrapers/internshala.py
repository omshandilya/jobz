import re
import time
import random
import logging
import hashlib
from typing import List, Dict, Any
from datetime import timedelta
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
    _STEALTH_AVAILABLE = False
    logger.warning("playwright-stealth not installed. Bot detection risk is higher.")


class InternshalaScraper(BaseScraper):
    def search(self, query: str, location: str, date_hours: int = 24) -> List[Dict[str, Any]]:
        # Format query and location for URL
        role = re.sub(r'\s+', '-', query.strip()).lower()
        loc = re.sub(r'\s+', '-', location.strip()).lower()

        url_base = f"https://internshala.com/jobs/keywords-{role}/location-{loc}"
        logger.info(f"InternshalaScraper: searching URL: {url_base}")

        raw_jobs = []

        with sync_playwright() as p:
            # Launch Chromium (Internshala works with Chromium; stealth reduces bot flags)
            browser = None
            try:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"]
                )
            except Exception as launch_err:
                logger.error(f"Failed to launch browser for Internshala: {launch_err}")
                return []

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1440, 'height': 900}
            )
            page = context.new_page()

            # Apply stealth patches to reduce bot detection fingerprint
            if _STEALTH_AVAILABLE:
                stealth_sync(page)
                logger.info("InternshalaScraper: playwright-stealth applied.")

            try:
                # Scrape up to 2 pages
                for page_num in range(1, 3):
                    if page_num == 1:
                        page_url = url_base
                    else:
                        page_url = f"{url_base}/page-{page_num}"

                    logger.info(f"Scraping Internshala page {page_num}: {page_url}")

                    try:
                        resp = page.goto(page_url, wait_until="networkidle", timeout=30000)
                    except Exception:
                        # Fallback to domcontentloaded if networkidle times out
                        try:
                            resp = page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
                        except Exception as nav_err:
                            logger.error(f"Navigation failed for Internshala page {page_num}: {nav_err}")
                            break

                    if resp and resp.status >= 400:
                        # Try alternate URL pattern
                        alt_url = f"https://internshala.com/jobs/{role}-jobs-in-{loc}"
                        if page_num > 1:
                            alt_url += f"/page-{page_num}"
                        logger.info(f"Trying alternate Internshala URL: {alt_url}")
                        try:
                            resp = page.goto(alt_url, wait_until="domcontentloaded", timeout=30000)
                        except Exception as alt_err:
                            logger.error(f"Alt URL also failed: {alt_err}")
                            break
                        if resp and resp.status >= 400:
                            logger.warning(f"Internshala returned {resp.status} on page {page_num}. Stopping.")
                            break

                    time.sleep(random.uniform(2.0, 3.5))

                    # Scroll to trigger lazy-loaded content
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
                    time.sleep(1.0)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1.0)

                    # Wait for at least one job card to appear
                    try:
                        page.wait_for_selector(
                            ".individual_internship, .internship_meta, [class*='job-container']",
                            timeout=10000
                        )
                    except Exception:
                        logger.warning(f"No job cards appeared on Internshala page {page_num} after wait.")
                        break

                    # Extract job cards from the rendered DOM
                    job_cards = page.query_selector_all(
                        ".individual_internship.jobs, .individual_internship, .internship_meta"
                    )
                    if not job_cards:
                        logger.info(f"No job cards found on Internshala page {page_num}.")
                        break

                    logger.info(f"Found {len(job_cards)} job cards on Internshala page {page_num}.")

                    for card in job_cards:
                        try:
                            # Title & URL
                            title_el = card.query_selector(
                                ".heading_4_5 a, .heading_5 a, a.view_detail_button, "
                                ".job-internship-name a, h3 a, h4 a"
                            )
                            if not title_el:
                                continue
                            title = title_el.inner_text().strip()
                            job_url = title_el.get_attribute("href") or ""
                            if job_url and not job_url.startswith("http"):
                                job_url = "https://internshala.com" + job_url

                            # Company
                            company_el = card.query_selector(
                                ".company_name a, .company_and_premium a, .company_name, [class*='company']"
                            )
                            company = company_el.inner_text().strip() if company_el else ""

                            # Location
                            loc_el = card.query_selector(
                                ".location_link, #location_names, .location, [class*='location']"
                            )
                            job_loc = loc_el.inner_text().strip() if loc_el else location

                            # Experience / Stipend
                            exp_el = card.query_selector(
                                ".experience_container, .stipend_container, .stipend, .salary, [class*='experience']"
                            )
                            experience = exp_el.inner_text().strip() if exp_el else "0-2 years"

                            # Posted date
                            posted_el = card.query_selector(
                                ".status-container, .status-inactive, .posted_by_container, [class*='posted']"
                            )
                            posted_str = posted_el.inner_text().strip() if posted_el else ""

                            if title and job_url:
                                raw_jobs.append({
                                    "title": title,
                                    "company": company,
                                    "location": job_loc,
                                    "experience_required": experience,
                                    "source_url": job_url,
                                    "posted_str": posted_str,
                                })
                        except Exception as e:
                            logger.error(f"Error parsing Internshala job card: {e}")

            except Exception as e:
                logger.error(f"Error during Internshala scraping: {e}")

            # Visit each job detail page to extract full JD text and company domain
            for raw_job in raw_jobs[:15]:
                try:
                    time.sleep(random.uniform(1.5, 3.0))
                    page.goto(raw_job["source_url"], wait_until="domcontentloaded", timeout=20000)
                    time.sleep(random.uniform(1.0, 2.0))

                    # Extract JD text from rendered page
                    jd_el = page.query_selector(
                        ".text-container, .job_description, .internship_details, "
                        ".detail_view, [class*='description'], [class*='jd']"
                    )
                    if jd_el:
                        jd_text = jd_el.inner_text().strip()
                    else:
                        jd_text = page.evaluate("() => document.body.innerText")[:2000]
                    raw_job["jd_text"] = jd_text

                    # Extract company domain — scan all links for external non-Internshala URLs
                    company_domain = ""
                    try:
                        all_links = page.query_selector_all("a[href]")
                        for link in all_links:
                            try:
                                href = link.get_attribute("href") or ""
                                text = link.inner_text().strip().lower()
                                if (
                                    href.startswith("http")
                                    and "internshala.com" not in href
                                    and any(w in text for w in ["website", "visit", "company", "www", "homepage"])
                                ):
                                    parsed = urlparse(href)
                                    netloc = parsed.netloc.replace("www.", "").strip()
                                    if netloc:
                                        company_domain = netloc
                                        break
                            except Exception:
                                continue
                    except Exception as link_err:
                        logger.debug(f"Link scan failed on {raw_job['source_url']}: {link_err}")

                    # Fallback: derive domain from cleaned company name
                    if not company_domain and raw_job.get("company"):
                        clean = re.sub(r'[^a-z0-9]', '', raw_job["company"].lower())
                        company_domain = f"{clean}.com" if clean else ""

                    raw_job["company_domain"] = company_domain

                except Exception as e:
                    logger.error(f"Error getting Internshala JD from {raw_job['source_url']}: {e}")
                    raw_job["jd_text"] = "Job description extraction failed."
                    clean = re.sub(r'[^a-z0-9]', '', raw_job.get("company", "").lower())
                    raw_job["company_domain"] = f"{clean}.com" if clean else ""

            browser.close()

        return self.normalize(raw_jobs)

    def normalize(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for raw in raw_jobs:
            posted_at = timezone.now()
            posted_str = raw.get("posted_str", "").lower()

            if "today" in posted_str or "just now" in posted_str:
                posted_at = timezone.now()
            elif "yesterday" in posted_str:
                posted_at = timezone.now() - timedelta(days=1)
            else:
                days_match = re.search(r'(\d+)\s*days?\s*ago', posted_str)
                if days_match:
                    days = int(days_match.group(1))
                    posted_at = timezone.now() - timedelta(days=days)

            title = raw.get("title", "")
            company = raw.get("company", "")
            source = "internshala"

            # dedup_hash = SHA256 of f"{title.lower()}{company.lower()}internshala"
            raw_dedup_str = f"{title.lower()}{company.lower()}internshala"
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
