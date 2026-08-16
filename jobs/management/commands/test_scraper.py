import os
from django.core.management.base import BaseCommand
from scraper.tasks import scrape_internshala, scrape_naukri, scrape_indeed, scrape_linkedin

class Command(BaseCommand):
    help = 'Tests the scrapers locally without Celery'

    def add_arguments(self, parser):
        parser.add_argument('--query', type=str, required=True, help='Search query (e.g., "backend engineer")')
        parser.add_argument('--location', type=str, required=True, help='Location (e.g., "delhi")')
        parser.add_argument('--source', type=str, required=False, help='Specific source to scrape (e.g., "linkedin", "internshala", "naukri", "indeed")')
        parser.add_argument('--date_hours', type=int, default=24, help='Hours back to search')

    def handle(self, *args, **options):
        query = options['query']
        location = options['location']
        source = options.get('source')
        date_hours = options['date_hours']

        self.stdout.write(self.style.SUCCESS(f'Testing scrapers for "{query}" in "{location}" (last {date_hours}h)'))

        if source:
            source = source.lower()
            if source == 'linkedin':
                self.stdout.write('Running LinkedInGoogleScraper...')
                # We call the task synchronously by unwrapping it from celery or just calling the python func
                scrape_linkedin(query, location, date_hours)
            elif source == 'internshala':
                self.stdout.write('Running InternshalaScraper...')
                scrape_internshala(query, location, date_hours)
            elif source == 'naukri':
                self.stdout.write('Running NaukriScraper...')
                scrape_naukri(query, location, date_hours)
            elif source == 'indeed':
                self.stdout.write('Running IndeedScraper...')
                scrape_indeed(query, location, date_hours)
            else:
                self.stderr.write(self.style.ERROR(f'Unknown source: {source}'))
        else:
            self.stdout.write('Running all scrapers sequentially...')
            
            self.stdout.write('--- Internshala ---')
            scrape_internshala(query, location, date_hours)
            
            self.stdout.write('--- Naukri ---')
            scrape_naukri(query, location, date_hours)
            
            self.stdout.write('--- Indeed ---')
            scrape_indeed(query, location, date_hours)
            
            self.stdout.write('--- LinkedIn ---')
            scrape_linkedin(query, location, date_hours)
            
        self.stdout.write(self.style.SUCCESS('Testing complete! Check database or logs for results.'))
