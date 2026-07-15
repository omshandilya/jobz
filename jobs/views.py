import re
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import Job, SearchQuery
from .serializers import JobListSerializer, JobDetailSerializer
from scraper.tasks import run_scrapers

class JobSearchPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class JobSearchView(APIView):
    def get(self, request, *args, **kwargs):
        q = request.query_params.get('q', '').strip()
        location = request.query_params.get('location', '').strip()
        
        # Default query params
        date_hours = int(request.query_params.get('date_hours', 24))
        min_score = float(request.query_params.get('min_score', 0.6))
        
        if not q:
            return Response(
                {"error": "Query parameter 'q' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Parse q into role and experience keywords
        # Extract experience numbers from the query if present
        exp_keywords = re.findall(r'\d+\s*(?:years?|yrs?|exp|experience)', q, re.IGNORECASE)
        role_keywords = q
        for keyword in exp_keywords:
            role_keywords = role_keywords.replace(keyword, "")
        
        role_words = [w.strip() for w in re.split(r'\s+', role_keywords) if w.strip()]
        
        # Check if we have recent results for this query + location (scraped within last 1 hour)
        recent_cutoff = timezone.now() - timedelta(hours=1)
        search_query, created = SearchQuery.objects.get_or_create(
            query=q.lower(),
            location=location.lower()
        )
        
        if (
            created or 
            not search_query.last_scraped_at or 
            search_query.last_scraped_at < recent_cutoff
        ):
            # Trigger celery scraper task asynchronously
            run_scrapers.delay(q, location, date_hours)
            search_query.last_scraped_at = timezone.now()
            search_query.save()
            
        # Query matching jobs from the DB
        queryset = Job.objects.filter(is_active=True, relevancy_score__gte=min_score)
        
        # Filter by date_hours
        cutoff_date = timezone.now() - timedelta(hours=date_hours)
        queryset = queryset.filter(Q(posted_at__gte=cutoff_date) | Q(fetched_at__gte=cutoff_date))
        
        # Filter by location if specified
        if location:
            queryset = queryset.filter(location__icontains=location)
            
        # Filter by parsed role words (any match in title or jd_text)
        if role_words:
            role_query = Q()
            for word in role_words:
                role_query |= Q(title__icontains=word) | Q(jd_text__icontains=word)
            queryset = queryset.filter(role_query)
            
        # Sort by relevancy_score DESC, then posted_at DESC
        queryset = queryset.order_by('-relevancy_score', '-posted_at')
        
        # Paginate results
        paginator = JobSearchPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request, view=self)
        
        serializer = JobListSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)


class JobDetailView(APIView):
    def get(self, request, uuid, *args, **kwargs):
        try:
            job = Job.objects.get(id=uuid, is_active=True)
            serializer = JobDetailSerializer(job)
            return Response(serializer.data)
        except Job.DoesNotExist:
            return Response(
                {"error": "Job not found."},
                status=status.HTTP_404_NOT_FOUND
            )
