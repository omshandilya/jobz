from rest_framework import serializers
from .models import Job

class JobListSerializer(serializers.ModelSerializer):
    jd_preview = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company', 'location', 'experience_required',
            'source', 'source_url', 'relevancy_score', 'skills_extracted',
            'posted_at', 'jd_preview'
        ]

    def get_jd_preview(self, obj):
        return obj.jd_text[:200] if obj.jd_text else ""


class JobDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = '__all__'
