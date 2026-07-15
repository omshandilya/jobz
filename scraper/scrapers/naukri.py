import time
import random
import re
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from django.utils import timezone
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from .base import BaseScraper

logger = logging.getLogger(__name__)

class NaukriScraper(BaseScraper):
    def search(self, query: str, location: str, date_hours: int = 24) -> List[Dict[str, Any]]:
        # Parse query for experience
        exp = 0
        exp_match = re.search(r'(\d+)\s*(?:years?|yrs?|exp|experience)', query, re.IGNORECASE)
        if exp_match:
            exp = int(exp_match.group(1))
        
        # Clean query to extract role name (remove experience keywords if present)
        role = re.sub(r'\d+\s*(?:years?|yrs?|exp|experience)', '', query, flags=re.IGNORECASE).strip()
        role = re.sub(r'\s+', '-', role).lower()
        
        # Format location
        loc = re.sub(r'\s+', '-', location.strip()).lower()
        
        # Build search URL
        # Naukri pattern: https://www.naukri.com/{role}-jobs-in-{location}?experience={exp}
        url = f"https://www.naukri.com/{role}-jobs-in-{loc}?experience={exp}"
        
        logger.info(f"NaukriScraper: searching URL: {url}")
        
        raw_jobs = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            stealth_sync(page)
            
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(random.uniform(2.0, 4.0))
                
                # Scrape up to 3 pages
                for page_num in range(1, 4):
                    logger.info(f"Scraping Naukri page {page_num}...")
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
                    time.sleep(1.0)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1.0)
                    
                    # Wait for job listings to load
                    # Common selectors: article.jobTuple, .srp-jobtuple, [data-job-id]
                    job_elements = page.query_selector_all("article.jobTuple, .srp-jobtuple, [class*='jobTuple']")
                    if not job_elements:
                        logger.warning(f"No job elements found on page {page_num}")
                        break
                        
                    for el in job_elements:
                        try:
                            # Title
                            title_el = el.query_selector("a.title, a.job-title, [class*='title']")
                            title = title_el.inner_text().strip() if title_el else ""
                            
                            # URL
                            job_url = title_el.get_attribute("href") if title_el else ""
                            if job_url and not job_url.startswith("http"):
                                job_url = "https://www.naukri.com" + job_url
                            
                            # Company
                            company_el = el.query_selector("a.comp-name, .companyName, [class*='company']")
                            company = company_el.inner_text().strip() if company_el else ""
                            
                            # Location
                            loc_el = el.query_selector(".locWdth, .location, [class*='location']")
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
                                    "source_url": job_url,
                                    "company": company,
                                    "location": job_loc,
                                    "experience_required": experience,
                                    "posted_str": posted_str,
                                })
                        except Exception as e:
                            logger.error(f"Error parsing job card: {e}")
                    
                    # Go to next page if page_num < 3
                    if page_num < 3:
                        next_btn = page.query_selector("a.styles_btn-secondary__25_C2:has-text('Next'), a:has-text('Next'), .styles_btn-secondary__25_C2")
                        if next_btn:
                            try:
                                next_btn.click()
                                time.sleep(random.uniform(2.0, 4.0))
                            except Exception as click_err:
                                logger.warning(f"Could not click next page button: {click_err}")
                                break
                        else:
                            break
                            
            except Exception as e:
                logger.error(f"Error scraping Naukri search results: {e}")
            
            # Now visit each job URL to extract full JD and company domain
            # Limit the requests to prevent getting blocked/timeout in demo
            for raw_job in raw_jobs[:15]:
                try:
                    time.sleep(random.uniform(2.0, 4.0))
                    page.goto(raw_job["source_url"], wait_until="domcontentloaded", timeout=20000)
                    
                    # Extract JD text
                    # Selectors for JD description in Naukri:
                    jd_el = page.query_selector(".job-desc, .description, section.job-desc, .jd-desc")
                    jd_text = jd_el.inner_text().strip() if jd_el else ""
                    if not jd_text:
                        # Fallback to general content container
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
                    raw_job["company_domain"] = company_domain
                    
                except Exception as e:
                    logger.error(f"Error fetching JD from {raw_job['source_url']}: {e}")
                    raw_job["jd_text"] = "Job description extraction failed."
                    raw_job["company_domain"] = ""
            
            browser.close()
            
        return raw_jobs

    def normalize(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for raw in raw_jobs:
            # Parse posted_str to a datetime
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
                "dedup_hash": self.generate_dedup_hash(title, company, source),
            })
        return normalized
