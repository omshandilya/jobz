from django.contrib import admin
from .models import Contact, OutreachLog

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['email', 'job', 'source', 'smtp_status', 'confidence_score', 'verified_at']
    search_fields = ['email', 'first_name', 'last_name', 'job__company']
    list_filter = ['source', 'smtp_status', 'is_catch_all']


@admin.register(OutreachLog)
class OutreachLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'job', 'contact', 'status', 'sent_at']
    search_fields = ['user__email', 'contact__email', 'email_subject']
    list_filter = ['status']
