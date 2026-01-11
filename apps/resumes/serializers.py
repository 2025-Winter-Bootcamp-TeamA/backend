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
    tech_stacks = ResumeStackSerializer(many=True, read_only=True)

    class Meta:
        model = Resume
        fields = ['id', 'title', 'url', 'tech_stacks', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ResumeMatchingSerializer(serializers.ModelSerializer):
    """이력서 매칭 시리얼라이저"""

    class Meta:
        model = ResumeMatching
        fields = ['id', 'matching_rate', 'feedback']
