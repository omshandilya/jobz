import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=200, blank=True)

    # Gmail OAuth fields
    gmail_access_token = models.TextField(blank=True)
    gmail_refresh_token = models.TextField(blank=True)
    gmail_email = models.CharField(max_length=200, blank=True)
    email_template = models.TextField(blank=True)
    gmail_connected_at = models.DateTimeField(null=True, blank=True)

    # Use email as the login identifier instead of username
    USERNAME_FIELD = 'email'
    # username is still required by AbstractUser — keep it but make it optional
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email

    @property
    def gmail_connected(self):
        return bool(self.gmail_access_token and self.gmail_email)
