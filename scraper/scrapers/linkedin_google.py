import re
import time
import random
import logging
import urllib.parse
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
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


class LinkedInGoogleScraper(BaseScraper):
    def search(self, query: str, location: str, date_hours: int = 24) -> List[Dict[str, Any]]:
        raw_jobs = []

        # 1. Build Google search URL
        google_query = f'site:linkedin.com/jobs/view "{query}" "{location}"'
        if date_hours <= 24:
            tbs = "qdr:d"
        elif date_hours <= 168:
            tbs = "qdr:w"
        else:
            tbs = ""
            
        tbs_param = f"&tbs={tbs}" if tbs else ""
        url = f"https://www.google.com/search?q={urllib.parse.quote(google_query)}&num=30{tbs_param}"
        
        logger.info(f"LinkedInGoogleScraper: searching URL: {url}")
        print(f"LinkedInGoogleScraper: searching URL: {url}")

        with sync_playwright() as p:
            browser = None
            try:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"]
                )
            except Exception as launch_err:
                logger.error(f"Failed to launch browser for LinkedInGoogleScraper: {launch_err}")
                print(f"Failed to launch browser for LinkedInGoogleScraper: {launch_err}")
                return []

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1440, 'height': 900}
            )
            page = context.new_page()

            if _STEALTH_AVAILABLE:
                stealth_sync(page)
                logger.info("LinkedInGoogleScraper: playwright-stealth applied.")

            try:
                # Go to Google
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Check for CAPTCHA
                page_text = page.evaluate("() => document.body.innerText").lower()
                if "unusual traffic" in page_text or "recaptcha" in page_text:
                    logger.warning("Google CAPTCHA encountered, skipping LinkedIn scrape")
                    print("Google CAPTCHA encountered, skipping LinkedIn scrape")
                    browser.close()
                    return []
                
                # Wait for search results
                try:
                    page.wait_for_selector("#search, div.g", timeout=10000)
                except Exception:
                    logger.warning("No search results appeared on Google.")
                    print("No search results appeared on Google.")
                    browser.close()
                    return []

                # Extract LinkedIn URLs
                linkedin_urls = []
                all_links = page.query_selector_all("a[href]")
                for link in all_links:
                    href = link.get_attribute("href") or ""
                    # Sometimes Google wraps urls in /url?q=
                    if "/url?q=" in href:
                        href = href.split("/url?q=")[1].split("&")[0]
                        href = urllib.parse.unquote(href)
                    
                    if "linkedin.com/jobs/view" in href:
                        if href not in linkedin_urls:
                            linkedin_urls.append(href)
                
                # Deduplicate and limit to 15
                linkedin_urls = linkedin_urls[:15]
                logger.info(f"Found {len(linkedin_urls)} LinkedIn job URLs via Google.")
                print(f"Found {len(linkedin_urls)} LinkedIn job URLs via Google.")
                
                time.sleep(random.uniform(2.0, 3.0))

            except Exception as e:
                logger.error(f"Error during Google scraping: {e}")
                print(f"Error during Google scraping: {e}")
                browser.close()
                return []

            # 2. Fetch each LinkedIn job page
            now = datetime.now(timezone.utc)
            for linkedin_url in linkedin_urls:
                try:
                    time.sleep(random.uniform(3.0, 5.0))
                    page.goto(linkedin_url, wait_until="domcontentloaded", timeout=30000)
                    
                    # Wait for title
                    try:
                        page.wait_for_selector("h1.top-card-layout__title, .job-details-jobs-unified-top-card__job-title", timeout=8000)
                    except Exception:
                        pass # proceed anyway to check jd_text
                    
                    # jd_text
                    jd_text = ""
                    jd_el = page.query_selector("div.show-more-less-html__markup, .jobs-description__content, #job-details")
                    if jd_el:
                        jd_text = jd_el.inner_text().strip()
                    
                    if not jd_text or len(jd_text) < 100:
                        logger.info(f"LinkedIn login wall hit or empty JD for {linkedin_url}. Skipping.")
                        continue
                        
                    # title
                    title_el = page.query_selector("h1.top-card-layout__title, .job-details-jobs-unified-top-card__job-title")
                    if title_el:
                        title = title_el.inner_text().strip()
                    else:
                        title = page.title().replace(" | LinkedIn", "").strip()
                        
                    # company
                    company = ""
                    company_url = ""
                    company_el = page.query_selector("a.topcard__org-name-link, .job-details-jobs-unified-top-card__company-name a")
                    if company_el:
                        company = company_el.inner_text().strip()
                        company_url = company_el.get_attribute("href") or ""
                        
                    # company_domain
                    company_domain = ""
                    if company_url:
                        if "/company/" in company_url:
                            clean = re.sub(r'[^a-z0-9]', '', company.lower())
                            company_domain = f"{clean}.com" if clean else ""
                        else:
                            parsed = urlparse(company_url)
                            netloc = parsed.netloc.replace("www.", "").strip()
                            if netloc:
                                company_domain = netloc
                    
                    if not company_domain and company:
                        clean = re.sub(r'[^a-z0-9]', '', company.lower())
                        company_domain = f"{clean}.com" if clean else ""
                        
                    # location
                    location_val = location
                    loc_el = page.query_selector("span.topcard__flavor--bullet, .job-details-jobs-unified-top-card__bullet")
                    if loc_el:
                        location_val = loc_el.inner_text().strip()
                        
                    # posted_at
                    posted_at = now
                    posted_el = page.query_selector("span.posted-time-ago__text, .job-details-jobs-unified-top-card__posted-date")
                    if posted_el:
                        posted_str = posted_el.inner_text().strip().lower()
                        # parse relative time
                        num_match = re.search(r'(\d+)', posted_str)
                        if num_match:
                            num = int(num_match.group(1))
                            if "hour" in posted_str:
                                posted_at = now - timedelta(hours=num)
                            elif "day" in posted_str:
                                posted_at = now - timedelta(days=num)
                            elif "week" in posted_str:
                                posted_at = now - timedelta(weeks=num)
                            elif "minute" in posted_str:
                                posted_at = now - timedelta(minutes=num)
                                
                    # experience_required
                    experience_required = ""
                    exp_match = re.search(r'(\d+)\+?\s*(?:to\s*\d+)?\s*years?', jd_text, re.IGNORECASE)
                    if exp_match:
                        experience_required = exp_match.group(0).strip()
                        
                    # dedup_hash
                    dedup_hash = self.generate_dedup_hash(title, company, "linkedin")
                    
                    raw_jobs.append({
                        "title": title,
                        "company": company,
                        "company_domain": company_domain,
                        "location": location_val,
                        "experience_required": experience_required,
                        "source": "linkedin",
                        "source_url": linkedin_url,
                        "jd_text": jd_text,
                        "posted_at": posted_at,
                        "dedup_hash": dedup_hash,
                    })

                except Exception as e:
                    logger.error(f"Error extracting LinkedIn job {linkedin_url}: {e}")
                    print(f"Error extracting LinkedIn job {linkedin_url}: {e}")
                    continue

            browser.close()

        # No normalize needed because we built it fully here
        return raw_jobs

    def normalize(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return raw_jobs
