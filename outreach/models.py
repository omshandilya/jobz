import uuid
from django.db import models
from django.conf import settings
from jobs.models import Job


class Contact(models.Model):
    SOURCE_CHOICES = [
        ('jd_extract', 'JD Extract'),
        ('hunter', 'Hunter.io'),
        ('smtp_pattern', 'SMTP Pattern'),
        ('manual', 'Manual'),
    ]

    SMTP_STATUS_CHOICES = [
        ('valid', 'Valid'),
        ('risky', 'Risky'),
        ('catch_all', 'Catch All'),
        ('not_found', 'Not Found'),
        ('unverified', 'Unverified'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='contacts')
    email = models.EmailField()
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=200, blank=True)
    department = models.CharField(max_length=100, blank=True)
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    smtp_status = models.CharField(max_length=50, choices=SMTP_STATUS_CHOICES, default='unverified')
    is_catch_all = models.BooleanField(default=False)
    confidence_score = models.FloatField(default=0.0)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-confidence_score', '-verified_at']
        unique_together = ('job', 'email')

    def __str__(self):
        return f"{self.email} ({self.job.company}) - {self.smtp_status}"


class OutreachLog(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    email_subject = models.CharField(max_length=500)
    email_body = models.TextField()
    gmail_message_id = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='queued')
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"Outreach to {self.contact.email} ({self.status})"
