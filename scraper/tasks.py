import logging
import os
from celery import shared_task
from django.db import connection
from django.utils import timezone
from jobs.models import Job, SearchQuery
from scraper.scrapers.internshala import InternshalaScraper
from scraper.scrapers.naukri import NaukriScraper
from scraper.scrapers.apify_naukri import ApifyNaukriScraper
from scraper.scrapers.apify_indeed import ApifyIndeedScraper
from scraper.filter import filter_jobs

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helper — dedup, filter, save
# ---------------------------------------------------------------------------

def _save_jobs(jobs_data: list, source_label: str = "") -> int:
    """
    Deduplicates a batch of normalized job dicts against each other and the DB,
    runs the Groq relevancy filter, then bulk-creates passing jobs.
    Returns the count of newly saved jobs.

    Calls connection.close() right before the DB write so that after the long
    scrape + Groq filtering period the worker gets a guaranteed fresh Supabase
    connection instead of a stale one that was silently dropped.
    """
    if not jobs_data:
        logger.info(f"[{source_label}] No jobs to save.")
        return 0

    tag = f"[{source_label}]" if source_label else ""

    # 1. Dedup within the batch
    unique: dict = {}
    for job in jobs_data:
        h = job.get("dedup_hash")
        if h and h not in unique:
            unique[h] = job

    # 2. Dedup against DB
    hashes = list(unique.keys())
    existing_hashes = set(
        Job.objects.filter(dedup_hash__in=hashes).values_list('dedup_hash', flat=True)
    )
    new_jobs = [job for h, job in unique.items() if h not in existing_hashes]

    if not new_jobs:
        logger.info(f"{tag} All {len(unique)} jobs already exist in DB.")
        return 0

    logger.info(f"{tag} {len(new_jobs)} new jobs to filter and save.")

    # 3. Groq relevancy filter (slow — may take many minutes for large batches)
    filtered = filter_jobs(new_jobs)

    if not filtered:
        logger.info(f"{tag} No jobs passed the relevancy filter (score >= 0.6).")
        return 0

    # 4. Build model objects
    job_objects = [
        Job(
            title=j.get('title', ''),
            company=j.get('company', ''),
            company_domain=j.get('company_domain', ''),
            location=j.get('location', ''),
            experience_required=j.get('experience_required', ''),
            source=j.get('source', ''),
            source_url=j.get('source_url', ''),
            jd_text=j.get('jd_text', ''),
            relevancy_score=j.get('relevancy_score', 0.5),
            skills_extracted=j.get('skills_extracted', []),
            posted_at=j.get('posted_at', timezone.now()),
            dedup_hash=j.get('dedup_hash', ''),
            is_active=True,
        )
        for j in filtered
    ]

    # 5. Close any stale connection from before the long scrape/filter period,
    #    then bulk-create with a guaranteed fresh Supabase connection.
    connection.close()
    try:
        created = Job.objects.bulk_create(job_objects, ignore_conflicts=True)
        count = len(created)
        logger.info(f"{tag} Saved {count} new jobs to DB.")
        print(f"{tag} Saved {count} new jobs to DB.")
        return count
    except Exception as db_err:
        logger.error(f"{tag} DB bulk_create failed: {db_err}")
        return 0


# ---------------------------------------------------------------------------
# Individual scraper tasks — each runs in its own Celery worker process
# ---------------------------------------------------------------------------

@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def scrape_internshala(self, query: str, location: str, date_hours: int = 24) -> int:
    """
    Fast scraper (~5-15s). Uses Playwright to scrape Internshala.
    Results appear in the UI within the initial 12s poll window.
    """
    # Close any stale DB connection inherited from a previous task
    connection.close()
    logger.info(f"[Internshala] Starting scrape: '{query}' in '{location}'")
    print(f"[Internshala] Scraping '{query}' in '{location}'...")

    try:
        scraper = InternshalaScraper()
        jobs = scraper.search(query, location, date_hours)
        print(f"[Internshala] Got {len(jobs)} jobs from scraper")
        return _save_jobs(jobs, source_label="Internshala")
    except Exception as exc:
        logger.error(f"[Internshala] Task error: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=1, default_retry_delay=60)
def scrape_naukri(self, query: str, location: str, date_hours: int = 24) -> int:
    """
    Medium-speed Apify scraper (~30-60s). Uses logiover/naukri-job-scraper.
    Falls back to local Playwright NaukriScraper if APIFY_API_KEY is not set.
    """
    connection.close()
    logger.info(f"[Naukri] Starting scrape: '{query}' in '{location}'")
    print(f"[Naukri] Scraping '{query}' in '{location}'...")

    try:
        if os.environ.get("APIFY_API_KEY"):
            scraper = ApifyNaukriScraper()
        else:
            logger.warning("[Naukri] No APIFY_API_KEY — falling back to Playwright scraper")
            scraper = NaukriScraper()

        jobs = scraper.search(query, location, date_hours)
        print(f"[Naukri] Got {len(jobs)} jobs from scraper")
        return _save_jobs(jobs, source_label="Naukri")
    except Exception as exc:
        logger.error(f"[Naukri] Task error: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=1, default_retry_delay=60)
def scrape_indeed(self, query: str, location: str, date_hours: int = 24) -> int:
    """
    Slow Apify scraper (~60-120s). Uses misceres/indeed-scraper.
    Only runs if APIFY_API_KEY is set.
    """
    connection.close()
    logger.info(f"[Indeed] Starting scrape: '{query}' in '{location}'")
    print(f"[Indeed] Scraping '{query}' in '{location}'...")

    if not os.environ.get("APIFY_API_KEY"):
        logger.warning("[Indeed] No APIFY_API_KEY — skipping Indeed scraper")
        print("[Indeed] Skipped — no APIFY_API_KEY")
        return 0

    try:
        scraper = ApifyIndeedScraper()
        jobs = scraper.search(query, location, date_hours)
        print(f"[Indeed] Got {len(jobs)} jobs from scraper")
        return _save_jobs(jobs, source_label="Indeed")
    except Exception as exc:
        logger.error(f"[Indeed] Task error: {exc}")
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Dispatcher — triggers all 3 scraper tasks
# ---------------------------------------------------------------------------

@shared_task
def run_scrapers(query: str, location: str, date_hours: int = 24) -> str:
    """
    Dispatches all 3 scraper tasks as independent Celery tasks.
    Internshala results appear fast (~10s); Naukri/Indeed appear later
    and are surfaced to the frontend via polling.
    """
    logger.info(f"Dispatching 3 scraper tasks for '{query}' in '{location}'")
    print(f"Dispatching scrapers: Internshala, Naukri, Indeed for '{query}' in '{location}'")

    scrape_internshala.delay(query, location, date_hours)
    scrape_naukri.delay(query, location, date_hours)
    scrape_indeed.delay(query, location, date_hours)

    return f"Dispatched 3 scraper tasks for '{query}' in '{location}'"


# ---------------------------------------------------------------------------
# Periodic task — re-scrapes all saved queries every 6 hours
# ---------------------------------------------------------------------------

@shared_task
def run_periodic_scrapers() -> str:
    """
    Beat-scheduled task. Dispatches all 3 scraper tasks for each saved SearchQuery.
    """
    queries = SearchQuery.objects.all()
    logger.info(f"Periodic scrape: triggering {queries.count()} saved queries")

    for q in queries:
        scrape_internshala.delay(q.query, q.location)
        scrape_naukri.delay(q.query, q.location)
        scrape_indeed.delay(q.query, q.location)
        q.last_scraped_at = timezone.now()
        q.save(update_fields=['last_scraped_at'])

    return f"Triggered 3-task scraping for {queries.count()} queries."
