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
    # 프론트/명세서에서 사용하는 필드명에 맞춘 매핑
    resume_id = serializers.IntegerField(source='id', read_only=True)
    resume_title = serializers.CharField(source='title')
    resume_url = serializers.CharField(source='url', allow_blank=True, allow_null=True, required=False)
    # 리스트 UI에서 사용하는 날짜 포맷(YYYY.MM.DD)으로 변환
    created_at = serializers.DateTimeField(format='%Y.%m.%d', read_only=True)
    # 보유 기술은 최대 3개까지만 노출
    tech_stacks = serializers.SerializerMethodField()

    class Meta:
        model = Resume
        fields = [
            'resume_id',
            'resume_title',
            'resume_url',
            'created_at',
            'tech_stacks',
        ]
        read_only_fields = ['resume_id', 'created_at']

    def get_tech_stacks(self, obj):
        """
        이력서에 연결된 보유 기술 중 최대 3개까지만 반환
        """
        # obj.tech_stacks: ResumeStack 역참조 (related_name='tech_stacks')
        stacks = obj.tech_stacks.select_related('tech_stack')[:3]
        return ResumeStackSerializer(stacks, many=True).data


class ResumeDetailSerializer(serializers.ModelSerializer):
    """이력서 상세 시리얼라이저"""
    tech_stacks = ResumeStackSerializer(many=True, read_only=True)

    class Meta:
        model = Resume
        fields = ['id', 'title', 'url', 'tech_stacks', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


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
