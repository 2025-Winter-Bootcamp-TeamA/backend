"""
이력서 시리얼라이저
"""

from rest_framework import serializers
from apps.trends.serializers import TechStackSerializer
from .models import Resume, ResumeStack, ResumeMatching


class ResumeStackSerializer(serializers.ModelSerializer):
    """이력서 기술 스택 시리얼라이저"""
    tech_stack = TechStackSerializer(read_only=True)

    class Meta:
        model = ResumeStack
        fields = ['tech_stack']


class ResumeSerializer(serializers.ModelSerializer):
    """이력서 시리얼라이저"""

    class Meta:
        model = Resume
        fields = ['id', 'title', 'url', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ResumeDetailSerializer(serializers.ModelSerializer):
    """이력서 상세 시리얼라이저"""

    resume_id = serializers.IntegerField(source='id', read_only=True)
    resume_title = serializers.CharField(source='title', read_only=True)
    resume_url = serializers.CharField(source='url', read_only=True)
    created_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S', read_only=True)
    tech_stacks = ResumeStackSerializer(many=True, read_only=True)

    class Meta:
        model = Resume
        fields = [
            'resume_id', 
            'resume_title',
            'resume_url',
            'tech_stacks',
            'created_at'
            ]
        read_only_fields = ['id', 'created_at']


class ResumeMatchingSerializer(serializers.ModelSerializer):
    """이력서 매칭 시리얼라이저"""
    job_posting_title = serializers.CharField(source='job_posting.title', read_only=True)
    resume_title = serializers.CharField(source='resume.title', read_only=True)

    class Meta:
        model = ResumeMatching
        fields = [
            'id', 'job_posting', 'resume', 'job_posting_title', 'resume_title',
            'score', 'feedback', 'question', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
