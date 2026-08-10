from rest_framework import serializers
from .models import Job, SearchQuery

class JobSerializer(serializers.ModelSerializer):
    jd_preview = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company', 'company_domain', 'location', 'experience_required',
            'source', 'source_url', 'relevancy_score', 'skills_extracted', 'posted_at',
            'jd_preview', 'is_active'
        ]

    def get_jd_preview(self, obj):
        return obj.jd_text[:200] if obj.jd_text else ""


class JobDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = '__all__'


class SearchQuerySerializer(serializers.ModelSerializer):
    raw_query = serializers.CharField(source='query')
    last_run_at = serializers.DateTimeField(source='last_scraped_at', read_only=True)
    date_filter_hours = serializers.IntegerField(default=24, read_only=True)

    class Meta:
        model = SearchQuery
        fields = ['id', 'raw_query', 'location', 'date_filter_hours', 'last_run_at']
