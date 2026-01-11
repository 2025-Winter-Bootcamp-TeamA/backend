"""
채용 공고 시리얼라이저
"""

from rest_framework import serializers
from apps.trends.serializers import TechStackSerializer
from .models import Corp, JobPosting, JobPostingStack, CorpBookmark


class CorpSerializer(serializers.ModelSerializer):
    """기업 시리얼라이저"""

    class Meta:
        model = Corp
        fields = ['id', 'name', 'logo_url', 'address']


class CorpDetailSerializer(serializers.ModelSerializer):
    """기업 상세 시리얼라이저"""
    job_posting_count = serializers.SerializerMethodField()

    class Meta:
        model = Corp
        fields = [
            'id', 'name', 'logo_url', 'address',
            'latitude', 'longitude', 'job_posting_count'
        ]

    def get_job_posting_count(self, obj):
        return obj.job_postings.filter(is_deleted=False).count()


class JobPostingStackSerializer(serializers.ModelSerializer):
    """채용 공고 기술 스택 시리얼라이저"""
    tech_stack = TechStackSerializer(read_only=True)

    class Meta:
        model = JobPostingStack
        fields = ['tech_stack']


class JobPostingSerializer(serializers.ModelSerializer):
    """채용 공고 시리얼라이저"""
    corp = CorpSerializer(read_only=True)

    class Meta:
        model = JobPosting
        fields = ['id', 'corp', 'url', 'title', 'stack_count', 'created_at']


class JobPostingDetailSerializer(serializers.ModelSerializer):
    """채용 공고 상세 시리얼라이저"""
    corp = CorpDetailSerializer(read_only=True)
    tech_stacks = JobPostingStackSerializer(many=True, read_only=True)

    class Meta:
        model = JobPosting
        fields = [
            'id', 'corp', 'url', 'title', 'description',
            'stack_count', 'tech_stacks', 'created_at'
        ]


class CorpBookmarkSerializer(serializers.ModelSerializer):
    """기업 즐겨찾기 시리얼라이저"""
    corp = CorpSerializer(read_only=True)

    class Meta:
        model = CorpBookmark
        fields = ['id', 'corp', 'created_at']
