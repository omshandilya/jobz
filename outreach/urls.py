from django.urls import path
from .views import JobContactsView

urlpatterns = [
    path('contacts/<uuid:job_uuid>/', JobContactsView.as_view(), name='outreach-job-contacts'),
]
