import time
import random
import re
import logging
import hashlib
from typing import List, Dict, Any
from datetime import datetime, timedelta
from django.utils import timezone
from playwright.sync_api import sync_playwright
from .base import BaseScraper

logger = logging.getLogger(__name__)

class NaukriScraper(BaseScraper):
    def search(self, query: str, location: str, date_hours: int = 24) -> List[Dict[str, Any]]:
        # Format query and location for URL
        exp_match = re.search(r'(\d+)\s*(?:years?|yrs?|exp|experience)', query, re.IGNORECASE)
        exp = int(exp_match.group(1)) if exp_match else 0
        
        role_cleaned = re.sub(r'\d+\s*(?:years?|yrs?|exp|experience)', '', query, flags=re.IGNORECASE).strip()
        role = re.sub(r'\s+', '-', role_cleaned).lower()
        loc = re.sub(r'\s+', '-', location.strip()).lower()
        
        # Search URL pattern
        url_base = f"https://www.naukri.com/{role}-jobs-in-{loc}"
        if exp > 0:
            url_base += f"?experience={exp}"

        logger.info(f"NaukriScraper: searching URL: {url_base}")
        
        raw_jobs = []
        
        with sync_playwright() as p:
            # Use Chrome channel if available, fallback to Firefox (both bypass Akamai 403 Bot protection)
            browser = None
            try:
                browser = p.chromium.launch(channel="chrome", headless=True, args=["--headless=new", "--disable-blink-features=AutomationControlled"])
            except Exception:
                try:
                    browser = p.firefox.launch(headless=True)
                except Exception as launch_err:
                    logger.error(f"Failed to launch browser for Naukri: {launch_err}")
                    return []

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            
            try:
                # Warmup session on homepage first to establish Akamai WAF cookies
                page.goto("https://www.naukri.com/", wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)
                
                # Max 2 pages of results
                for page_num in range(1, 3):
                    page_url = url_base if page_num == 1 else f"{url_base}-{page_num}"
                    logger.info(f"Scraping Naukri page {page_num}: {page_url}")
                    
                    resp = page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(random.uniform(3.0, 5.0))
                    
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
                    time.sleep(1.0)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1.0)
                    
                    # Job tuple cards on Naukri
                    job_elements = page.query_selector_all("div.srp-jobtuple-wrapper, article.jobTuple, div.cust-job-tuple, [class*='srp-jobtuple'], [class*='cust-job-tuple']")
                    if not job_elements:
                        logger.warning(f"No job elements found on page {page_num} (Status: {resp.status if resp else 'N/A'})")
                        break
                        
                    for el in job_elements:
                        try:
                            # Title & URL
                            title_el = el.query_selector("a.title, [class*='title']")
                            title = title_el.inner_text().strip() if title_el else ""
                            
                            job_url = title_el.get_attribute("href") if title_el else ""
                            if job_url and not job_url.startswith("http"):
                                job_url = "https://www.naukri.com" + job_url
                            
                            # Company
                            company_el = el.query_selector("a.comp-name, [class*='comp-name'], [class*='company']")
                            company = company_el.inner_text().strip() if company_el else ""
                            
                            # Location
                            loc_el = el.query_selector(".locWdth, .location, [class*='location'], [class*='loc']")
                            job_loc = loc_el.inner_text().strip() if loc_el else location
                            
                            # Experience
                            exp_el = el.query_selector(".expwdth, .experience, [class*='exp']")
                            experience = exp_el.inner_text().strip() if exp_el else ""
                            
                            # Posted Date Info
                            posted_el = el.query_selector(".posted, .job-post-day, [class*='posted'], [class*='date']")
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
                            logger.error(f"Error parsing Naukri job card: {e}")
                            
            except Exception as e:
                logger.error(f"Error scraping Naukri search results: {e}")
            
            # Visit each job detail URL to extract full JD text and company domain
            for raw_job in raw_jobs[:10]:
                try:
                    time.sleep(random.uniform(2.0, 4.0))
                    page.goto(raw_job["source_url"], wait_until="domcontentloaded", timeout=20000)
                    
                    # Extract full JD text
                    jd_el = page.query_selector(".job-desc, .description, section.job-desc, .jd-desc")
                    jd_text = jd_el.inner_text().strip() if jd_el else ""
                    if not jd_text:
                        jd_text = page.evaluate("() => document.body.innerText")[:2000]
                    raw_job["jd_text"] = jd_text
                    
                    # Extract company domain
                    company_link = page.query_selector("a[href*='http']:has-text('Website'), a.website-link, a[class*='website']")
                    company_domain = ""
                    if company_link:
                        href = company_link.get_attribute("href")
                        if href:
                            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', href)
                            if domain_match:
                                company_domain = domain_match.group(1)
                    
                    if not company_domain and raw_job.get("company"):
                        clean_comp = re.sub(r'[^a-zA-Z0-9]', '', raw_job["company"]).lower()
                        company_domain = f"{clean_comp}.com"
                        
                    raw_job["company_domain"] = company_domain
                    
                except Exception as e:
                    logger.error(f"Error fetching JD from {raw_job['source_url']}: {e}")
                    raw_job["jd_text"] = "Job description extraction failed."
                    clean_comp = re.sub(r'[^a-zA-Z0-9]', '', raw_job.get("company", "")).lower()
                    raw_job["company_domain"] = f"{clean_comp}.com" if clean_comp else ""
            
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
            source = "naukri"
            
            # dedup_hash = SHA256 of f"{title.lower()}{company.lower()}naukri"
            raw_dedup_str = f"{title.lower()}{company.lower()}naukri"
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
