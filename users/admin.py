from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'name', 'gmail_connected', 'is_active', 'date_joined']
    search_fields = ['email', 'name', 'gmail_email']
    readonly_fields = ['id', 'date_joined', 'last_login', 'gmail_connected_at']
    list_filter = ['is_active', 'is_staff']
