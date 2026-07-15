from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.exists and admin.site.urls or admin.site.urls), # standard mapping
    path('api/jobs/', include('jobs.urls')),
]
