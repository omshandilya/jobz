import logging
from concurrent.futures import ThreadPoolExecutor
from celery import shared_task
from django.utils import timezone
from jobs.models import Job, SearchQuery
from scraper.scrapers.naukri import NaukriScraper
from scraper.scrapers.internshala import InternshalaScraper
from scraper.filter import filter_jobs

logger = logging.getLogger(__name__)

def execute_scraper_search(scraper, query, location, date_hours):
    try:
        results = scraper.search(query, location, date_hours)
        return results
    except Exception as e:
        logger.error(f"Error running scraper {scraper.__class__.__name__}: {e}")
        return []

@shared_task
def run_scrapers(query: str, location: str, date_hours: int = 24) -> int:
    """
    Runs both scrapers (Naukri and Internshala), checks for duplicate dedup_hashes in DB,
    applies AI relevance filtering, and saves new matching jobs to DB via bulk_create.
    Can be run directly or via Celery.
    """
    logger.info(f"Starting run_scrapers task for query='{query}', location='{location}', date_hours={date_hours}")
    
    naukri = NaukriScraper()
    internshala = InternshalaScraper()
    
    # Run scrapers in parallel using ThreadPoolExecutor
    scraped_jobs = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(execute_scraper_search, naukri, query, location, date_hours),
            executor.submit(execute_scraper_search, internshala, query, location, date_hours)
        ]
        for future in futures:
            scraped_jobs.extend(future.result())
            
    if not scraped_jobs:
        logger.info("No jobs scraped.")
        return 0
        
    # Deduplicate within the scraped batch itself
    unique_scraped = {}
    for job in scraped_jobs:
        dedup_hash = job.get("dedup_hash")
        if dedup_hash and dedup_hash not in unique_scraped:
            unique_scraped[dedup_hash] = job
        
    # Deduplicate against the database
    hashes = list(unique_scraped.keys())
    existing_hashes = set(
        Job.objects.filter(dedup_hash__in=hashes).values_list('dedup_hash', flat=True)
    )
    
    new_jobs_data = [
        job for hash_val, job in unique_scraped.items()
        if hash_val not in existing_hashes
    ]
    
    if not new_jobs_data:
        logger.info("All scraped jobs already exist in the database.")
        return 0
        
    # Run relevancy filter on new jobs
    filtered_jobs_data = filter_jobs(new_jobs_data)
    
    if not filtered_jobs_data:
        logger.info("No new jobs passed the relevancy filter.")
        return 0
        
    # Prepare Django model objects
    job_objects = [
        Job(
            title=job.get('title', ''),
            company=job.get('company', ''),
            company_domain=job.get('company_domain', ''),
            location=job.get('location', ''),
            experience_required=job.get('experience_required', ''),
            source=job.get('source', ''),
            source_url=job.get('source_url', ''),
            jd_text=job.get('jd_text', ''),
            relevancy_score=job.get('relevancy_score', 0.5),
            skills_extracted=job.get('skills_extracted', []),
            posted_at=job.get('posted_at', timezone.now()),
            dedup_hash=job.get('dedup_hash', ''),
            is_active=True
        )
        for job in filtered_jobs_data
    ]
    
    # Bulk save to DB via bulk_create
    created_jobs = Job.objects.bulk_create(job_objects, ignore_conflicts=True)
    count = len(created_jobs)
    
    logger.info(f"Successfully added {count} new jobs to the database.")
    return count

@shared_task
def run_periodic_scrapers() -> str:
    """
    Periodic task for running scrapers across saved queries.
    """
    queries = SearchQuery.objects.all()
    logger.info(f"Running periodic scrapers for {queries.count()} saved queries.")
    
    for q in queries:
        try:
            run_scrapers.delay(q.query, q.location)
        except Exception:
            run_scrapers(q.query, q.location)
        q.last_scraped_at = timezone.now()
        q.save(update_fields=['last_scraped_at'])
        
    return f"Triggered scraping for {queries.count()} queries."
