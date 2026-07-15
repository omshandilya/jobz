import re
import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from datetime import datetime, timedelta
from django.utils import timezone
from .base import BaseScraper

logger = logging.getLogger(__name__)

class InternshalaScraper(BaseScraper):
    def search(self, query: str, location: str, date_hours: int = 24) -> List[Dict[str, Any]]:
        # Format query and location for the URL
        # E.g. "software-engineer" and "delhi"
        role = re.sub(r'\s+', '-', query.strip()).lower()
        loc = re.sub(r'\s+', '-', location.strip()).lower()
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        raw_jobs = []
        
        # Scrape up to 3 pages
        for page_num in range(1, 4):
            # Base URL format for page 1 vs others
            if page_num == 1:
                url = f"https://internshala.com/jobs/{role}-jobs-in-{loc}"
            else:
                url = f"https://internshala.com/jobs/{role}-jobs-in-{loc}/page-{page_num}"
                
            logger.info(f"InternshalaScraper: fetching URL: {url}")
            
            try:
                time.sleep(random.uniform(1.5, 3.0))
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch page {page_num}: Status {response.status_code}")
                    break
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Job cards on Internshala
                job_cards = soup.select(".individual_internship.jobs, .individual_internship")
                if not job_cards:
                    logger.info("No more job cards found on page.")
                    break
                    
                for card in job_cards:
                    try:
                        # Extract title and URL
                        title_el = card.select_one(".heading_4_5 a, .heading_5 a, a.view_detail_button")
                        if not title_el:
                            continue
                        title = title_el.get_text(strip=True)
                        job_url = title_el.get("href", "")
                        if job_url and not job_url.startswith("http"):
                            job_url = "https://internshala.com" + job_url
                            
                        # Company
                        company_el = card.select_one(".company_name a, .company_and_premium a, .company_name")
                        company = company_el.get_text(strip=True) if company_el else ""
                        
                        # Location
                        loc_el = card.select_one(".location_link, #location_names, .location")
                        job_loc = loc_el.get_text(strip=True) if loc_el else location
                        
                        # Stipend/Salary
                        stipend_el = card.select_one(".stipend_container, .stipend, .salary")
                        stipend = stipend_el.get_text(strip=True) if stipend_el else ""
                        
                        # Posted Date Info
                        posted_el = card.select_one(".status-container, .status-inactive, .posted_by_container")
                        posted_str = posted_el.get_text(strip=True) if posted_el else ""
                        
                        if title and job_url:
                            raw_jobs.append({
                                "title": title,
                                "source_url": job_url,
                                "company": company,
                                "location": job_loc,
                                "experience_required": stipend, # Using stipend/salary for experience_required or general stipend info
                                "posted_str": posted_str,
                            })
                    except Exception as e:
                        logger.error(f"Error parsing Internshala job card: {e}")
                        
            except Exception as e:
                logger.error(f"Error requesting Internshala page {page_num}: {e}")
                break
                
        # Visit each job page to get the full job description (JD)
        # Limit details queries to prevent speed blocking/timeouts
        for raw_job in raw_jobs[:15]:
            try:
                time.sleep(random.uniform(1.5, 3.0))
                detail_resp = requests.get(raw_job["source_url"], headers=headers, timeout=15)
                if detail_resp.status_code == 200:
                    detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                    
                    # Extract JD text
                    # Look for details container:
                    jd_container = detail_soup.select_one(".text-container, .job_description, .internship_details, .detail_view")
                    if jd_container:
                        jd_text = jd_container.get_text(separator="\n", strip=True)
                    else:
                        jd_text = detail_soup.get_text(separator="\n", strip=True)[:2000]
                    raw_job["jd_text"] = jd_text
                    
                    # Check for company domain (Internshala sometimes has website links)
                    company_link = detail_soup.select_one("a[href*='http']:has-text('Website'), a.website-link")
                    company_domain = ""
                    if company_link:
                        href = company_link.get("href")
                        if href:
                            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', href)
                            if domain_match:
                                company_domain = domain_match.group(1)
                    raw_job["company_domain"] = company_domain
                else:
                    raw_job["jd_text"] = "Job description extraction failed."
                    raw_job["company_domain"] = ""
            except Exception as e:
                logger.error(f"Error getting Internshala JD from {raw_job['source_url']}: {e}")
                raw_job["jd_text"] = "Job description extraction failed."
                raw_job["company_domain"] = ""
                
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
            source = "internshala"
            
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
