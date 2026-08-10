from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from jobs.models import Job
from .models import Contact
from .serializers import ContactSerializer
from .email_finder import find_emails_for_job


class JobContactsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_uuid=None, pk=None, *args, **kwargs):
        target_id = job_uuid or pk
        if not target_id:
            return Response(
                {"error": "job_uuid is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            job = Job.objects.get(id=target_id)
        except Job.DoesNotExist:
            return Response(
                {"error": "Job not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if contacts already exist in DB for this job (fetched within last 24h)
        cutoff_24h = timezone.now() - timedelta(hours=24)
        existing_contacts = Contact.objects.filter(job=job)
        
        has_recent_contacts = (
            existing_contacts.exists() and 
            existing_contacts.filter(verified_at__gte=cutoff_24h).exists()
        )

        if has_recent_contacts:
            contacts = existing_contacts.order_by('-confidence_score', '-verified_at')
        else:
            contacts = find_emails_for_job(str(job.id))

        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)
