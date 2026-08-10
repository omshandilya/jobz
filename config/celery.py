import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('jobzzzz')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps.
app.autodiscover_tasks()

# Beat schedule: run_scrapers every 6 hours for any saved search queries
app.conf.beat_schedule = {
    'run-scrapers-every-6-hours': {
        'task': 'scraper.tasks.run_periodic_scrapers',
        'schedule': crontab(minute=0, hour='*/6'),
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
