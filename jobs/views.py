import re
import time
import math
import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Job, SearchQuery
from .serializers import JobSerializer, JobDetailSerializer, SearchQuerySerializer
from scraper.tasks import run_scrapers

logger = logging.getLogger(__name__)

class JobSearchView(APIView):
    def get(self, request, *args, **kwargs):
        q = request.query_params.get('q', '').strip()
        location = request.query_params.get('location', '').strip() or 'india'
        
        try:
            date_hours = int(request.query_params.get('date_hours', 24))
        except (ValueError, TypeError):
            date_hours = 24

        try:
            min_score = float(request.query_params.get('min_score', 0.6))
        except (ValueError, TypeError):
            min_score = 0.6

        try:
            page = int(request.query_params.get('page', 1))
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1

        try:
            page_size = int(request.query_params.get('page_size', 20))
            if page_size < 1:
                page_size = 20
        except (ValueError, TypeError):
            page_size = 20

        if not q:
            return Response(
                {"error": "Query parameter 'q' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # a. Save/update SearchQuery in DB
        search_query, created = SearchQuery.objects.get_or_create(
            query=q.lower(),
            location=location.lower()
        )

        # b. Check if jobs exist in DB for this query fetched in last 1 hour
        recent_cutoff = timezone.now() - timedelta(hours=1)
        has_recent_results = (
            not created and
            search_query.last_scraped_at is not None and
            search_query.last_scraped_at >= recent_cutoff
        )

        # c. If no recent results: trigger run_scrapers.delay and wait up to 30s polling DB every 3s
        if not has_recent_results:
            start_time = timezone.now()
            try:
                run_scrapers.delay(q, location, date_hours)
            except Exception as e:
                logger.warning(f"Celery/Redis unavailable ({e}), running scrapers synchronously.")
                run_scrapers(q, location, date_hours)

            search_query.last_scraped_at = timezone.now()
            search_query.save()

            # Poll DB up to 30 seconds (every 3 seconds) for new results
            for _ in range(10):
                time.sleep(3)
                new_jobs_count = Job.objects.filter(
                    is_active=True,
                    relevancy_score__gte=min_score,
                    fetched_at__gte=start_time
                ).count()
                if new_jobs_count > 0:
                    break

        # d. Query jobs table: filter by relevancy_score >= min_score, posted_at/fetched_at >= now - date_hours, is_active=True
        queryset = Job.objects.filter(is_active=True, relevancy_score__gte=min_score)
        
        cutoff_date = timezone.now() - timedelta(hours=date_hours)
        queryset = queryset.filter(Q(posted_at__gte=cutoff_date) | Q(fetched_at__gte=cutoff_date))

        if location and location.lower() != 'all':
            queryset = queryset.filter(location__icontains=location)

        # e. Search filter: jobs where title or jd_text icontains any word from q
        words = [w.strip() for w in re.split(r'\s+', q) if w.strip()]
        if words:
            word_query = Q()
            for word in words:
                word_query |= Q(title__icontains=word) | Q(jd_text__icontains=word)
            queryset = queryset.filter(word_query)

        # f. Sort: relevancy_score DESC, posted_at DESC
        queryset = queryset.order_by('-relevancy_score', '-posted_at')

        # g. Paginate and return response: {"count": 45, "page": 1, "total_pages": 3, "results": [...jobs]}
        count = queryset.count()
        total_pages = math.ceil(count / page_size) if count > 0 else 1

        start = (page - 1) * page_size
        end = start + page_size
        paginated_jobs = queryset[start:end]

        serializer = JobSerializer(paginated_jobs, many=True)

        return Response({
            "count": count,
            "page": page,
            "total_pages": total_pages,
            "results": serializer.data
        })


class JobDetailView(APIView):
    def get(self, request, uuid=None, pk=None, *args, **kwargs):
        job_id = uuid or pk
        try:
            job = Job.objects.get(id=job_id, is_active=True)
            serializer = JobDetailSerializer(job)
            return Response(serializer.data)
        except Job.DoesNotExist:
            return Response(
                {"error": "Job not found."},
                status=status.HTTP_404_NOT_FOUND
            )
