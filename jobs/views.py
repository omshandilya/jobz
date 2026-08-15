import re
import time
import math
import logging
import threading
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Job, SearchQuery
from .serializers import JobSerializer, JobDetailSerializer
from scraper.tasks import run_scrapers, scrape_internshala, scrape_naukri, scrape_indeed

logger = logging.getLogger(__name__)

# How long after a search was triggered do we consider scrapers potentially still running?
_SCRAPING_ACTIVE_WINDOW_SECONDS = 180  # 3 minutes


class JobSearchView(APIView):
    permission_classes = [AllowAny]

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
            page = max(1, int(request.query_params.get('page', 1)))
        except (ValueError, TypeError):
            page = 1

        try:
            page_size = max(1, int(request.query_params.get('page_size', 20)))
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

        # b. Check if scrapers were triggered recently (within 1 hour)
        recent_cutoff = timezone.now() - timedelta(hours=1)
        has_recent_results = (
            not created and
            search_query.last_scraped_at is not None and
            search_query.last_scraped_at >= recent_cutoff
        )

        # c. If not recently scraped, dispatch all 3 Celery tasks
        if not has_recent_results:
            start_time = timezone.now()

            dispatched_via_celery = False
            try:
                # Dispatch all 3 tasks independently so each saves to DB as it finishes
                scrape_internshala.delay(q, location, date_hours)
                scrape_naukri.delay(q, location, date_hours)
                scrape_indeed.delay(q, location, date_hours)
                dispatched_via_celery = True
                logger.info(f"Dispatched 3 Celery scraper tasks for '{q}' in '{location}'")
            except Exception as celery_err:
                # Celery worker not reachable — fall back to background thread
                logger.warning(
                    f"Celery dispatch failed ({celery_err}), falling back to threading.Thread"
                )
                def _run_bg():
                    try:
                        run_scrapers(q, location, date_hours)
                    except Exception as err:
                        logger.error(f"Background scraper error: {err}")
                threading.Thread(target=_run_bg, daemon=True).start()

            search_query.last_scraped_at = timezone.now()
            search_query.save()

            # d. Poll DB for up to 12s waiting for Internshala results (fast scraper)
            words = [w.strip() for w in re.split(r'\s+', q) if w.strip()]
            existing_matching = Job.objects.filter(is_active=True, relevancy_score__gte=min_score)
            if words:
                wq = Q()
                for w in words:
                    wq |= Q(title__icontains=w) | Q(jd_text__icontains=w)
                existing_matching = existing_matching.filter(wq)

            if not existing_matching.exists():
                for _ in range(8):
                    time.sleep(1.5)
                    new_count = Job.objects.filter(
                        is_active=True,
                        relevancy_score__gte=min_score,
                        fetched_at__gte=start_time,
                    ).count()
                    if new_count > 0:
                        break

        # e. Build queryset
        queryset = Job.objects.filter(is_active=True, relevancy_score__gte=min_score)

        cutoff_date = timezone.now() - timedelta(hours=date_hours)
        queryset = queryset.filter(Q(posted_at__gte=cutoff_date) | Q(fetched_at__gte=cutoff_date))

        if location and location.lower() != 'all':
            queryset = queryset.filter(location__icontains=location)

        words = [w.strip() for w in re.split(r'\s+', q) if w.strip()]
        if words:
            word_query = Q()
            for word in words:
                word_query |= Q(title__icontains=word) | Q(jd_text__icontains=word)
            queryset = queryset.filter(word_query)

        queryset = queryset.order_by('-relevancy_score', '-posted_at')

        # f. Paginate
        count = queryset.count()
        total_pages = math.ceil(count / page_size) if count > 0 else 1
        paginated_jobs = queryset[(page - 1) * page_size: page * page_size]

        serializer = JobSerializer(paginated_jobs, many=True)

        # g. scraping_active = True if scrapers were triggered within the last 3 minutes
        #    Frontend uses this to decide whether to keep polling for new jobs.
        scraping_active = (
            search_query.last_scraped_at is not None and
            search_query.last_scraped_at >= timezone.now() - timedelta(seconds=_SCRAPING_ACTIVE_WINDOW_SECONDS)
        )

        return Response({
            "count": count,
            "page": page,
            "total_pages": total_pages,
            "scraping_active": scraping_active,
            "results": serializer.data,
        })


class JobDetailView(APIView):
    permission_classes = [AllowAny]

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
