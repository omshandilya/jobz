from rest_framework import serializers
from .models import Contact, OutreachLog

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            'id', 'email', 'first_name', 'last_name', 'title',
            'department', 'source', 'smtp_status', 'confidence_score'
        ]


class OutreachLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutreachLog
        fields = '__all__'
