from django.urls import path
from .views import JobSearchView, JobDetailView

urlpatterns = [
    path('search/', JobSearchView.as_view(), name='job-search'),
    path('<uuid:uuid>/', JobDetailView.as_view(), name='job-detail'),
]
