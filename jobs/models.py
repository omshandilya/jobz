import uuid
from django.db import models

class Job(models.Model):
    SOURCE_CHOICES = [
        ('naukri', 'Naukri'),
        ('internshala', 'Internshala'),
        ('indeed', 'Indeed'),
        ('instahyre', 'Instahyre'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    company_domain = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200)
    experience_required = models.CharField(max_length=500, blank=True)
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    source_url = models.URLField(max_length=500)
    jd_text = models.TextField()
    relevancy_score = models.FloatField(default=0.0)
    skills_extracted = models.JSONField(default=list)
    posted_at = models.DateTimeField(null=True, blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)
    dedup_hash = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-relevancy_score', '-posted_at']

    def __str__(self):
        return f"{self.title} at {self.company} ({self.source})"


class SearchQuery(models.Model):
    query = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    last_scraped_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('query', 'location')
        verbose_name_plural = "Search Queries"

    def __str__(self):
        return f"{self.query} in {self.location}"
