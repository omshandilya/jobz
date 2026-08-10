from django.core.management.base import BaseCommand
from scraper.tasks import run_scrapers
from jobs.models import Job

class Command(BaseCommand):
    help = 'Test running scrapers for a query and location'

    def add_arguments(self, parser):
        parser.add_argument('--query', '-q', type=str, required=True, help='Job title or query keyword')
        parser.add_argument('--location', '-l', type=str, default='', help='Location filter')

    def handle(self, *args, **options):
        query = options['query']
        location = options['location']

        self.stdout.write(self.style.NOTICE(f"Executing run_scrapers directly for query='{query}', location='{location}'..."))

        # Call run_scrapers directly
        new_count = run_scrapers(query, location)

        self.stdout.write(self.style.SUCCESS(f"\nScraping complete! New jobs saved: {new_count}\n"))

        # Fetch recent jobs to display in table
        recent_jobs = Job.objects.order_by('-fetched_at')[:25]

        header = f"{'Title':<32} | {'Company':<22} | {'Source':<12} | {'Score':<6} | {'URL':<40}"
        self.stdout.write(header)
        self.stdout.write("-" * len(header))

        for job in recent_jobs:
            title = (job.title[:29] + "...") if len(job.title) > 32 else job.title
            company = (job.company[:19] + "...") if len(job.company) > 22 else job.company
            source = job.source
            score = f"{job.relevancy_score:.2f}"
            url = (job.source_url[:37] + "...") if len(job.source_url) > 40 else job.source_url

            self.stdout.write(f"{title:<32} | {company:<22} | {source:<12} | {score:<6} | {url:<40}")

        self.stdout.write(self.style.SUCCESS(f"\nTotal new jobs saved in DB: {new_count}"))
