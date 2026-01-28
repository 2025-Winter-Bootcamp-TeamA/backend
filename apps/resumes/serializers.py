import os
from rest_framework import serializers
from django.core.files.storage import default_storage
from apps.trends.serializers import TechStackSerializer
from .models import Resume, ResumeStack, ResumeMatching, WorkExperience, ProjectExperience

class ResumeStackSerializer(serializers.ModelSerializer):
    """이력서 기술 스택 시리얼라이저"""
    tech_stack = TechStackSerializer(read_only=True)

    class Meta:
        model = ResumeStack
        fields = ['tech_stack']

class ResumeSerializer(serializers.ModelSerializer):
    """
    이력서 목록 및 업로드용 시리얼라이저
    - 목록 조회 시: get_tech_stacks 사용
    - 업로드 시: create() 사용
    """

    # 목록 조회용 (read_only)
    resume_id = serializers.IntegerField(source='id', read_only=True)
    resume_title = serializers.CharField(source='title', read_only=True)
    resume_url = serializers.CharField(source='url', read_only=True, allow_blank=True, allow_null=True)
    created_at = serializers.DateTimeField(format='%Y.%m.%d', read_only=True)

    tech_stacks = serializers.SerializerMethodField()

    # 업로드용
    file = serializers.FileField(write_only=True, required=True)
    title = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Resume
        fields = [
        'resume_id', 'resume_title', 'resume_url', 'tech_stacks',
        'title', 'file', 'created_at', 'updated_at']
        read_only_fields = ['id', 'url', 'created_at', 'updated_at']

    def get_tech_stacks(self, obj):
        """
        이력서에 연결된 보유 기술 중 최대 3개까지만 반환
        """
        stacks = obj.tech_stacks.select_related('tech_stack')[:3]
        return ResumeStackSerializer(stacks, many=True).data

    def create(self, validated_data):
        file_obj = validated_data.pop('file', None)
        user = self.context['request'].user
        
        # 제목 자동 추출
        title = validated_data.pop('title', None)
        if (not title or title.strip() == "") and file_obj:
            title = os.path.splitext(file_obj.name)[0]
        
        resume = Resume.objects.create(user=user, title=title, **validated_data)
        
        if file_obj:
            file_path = f"resumes/user_{user.id}/{resume.id}_{file_obj.name}"
            saved_path = default_storage.save(file_path, file_obj)
            resume.url = default_storage.url(saved_path)
            resume.save()

            # 기술 스택 저장 로직 (현재는 빈 상태로 유지)
            extracted_tech_stack_ids = [] # 추후 분석 로직 연동
            for ts_id in extracted_tech_stack_ids:
                ResumeStack.objects.create(resume=resume, tech_stack_id=ts_id)
            
        return resume

class ResumeDetailSerializer(serializers.ModelSerializer):
    """이력서 상세 정보 조회용 시리얼라이저"""

    resume_id = serializers.IntegerField(source='id', read_only=True)
    resume_title = serializers.CharField(source='title', read_only=True)
    resume_url = serializers.CharField(source='url', read_only=True)
    created_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S', read_only=True)
    tech_stacks = ResumeStackSerializer(many=True, read_only=True)
    extracted_text = serializers.SerializerMethodField()

    class Meta:
        model = Resume
        fields = ['resume_id', 'resume_title', 'resume_url', 'tech_stacks', 'extracted_text', 'created_at', 'updated_at']
        read_only_fields = ['id', 'url', 'created_at', 'updated_at']

    def get_extracted_text(self, obj):
        # retrieve 메서드에서 이미 추가되므로 여기서는 None 반환
        # 실제 값은 views.py의 retrieve 메서드에서 설정됨
        return getattr(obj, '_extracted_text', None)


class ResumeMatchingSerializer(serializers.ModelSerializer):
    """이력서 매칭 정보 시리얼라이저"""
    job_posting_title = serializers.CharField(source='job_posting.title', read_only=True)
    resume_title = serializers.CharField(source='resume.title', read_only=True)
    job_posting_corp_id = serializers.IntegerField(source='job_posting.corp_id', read_only=True)

    class Meta:
        model = ResumeMatching
        fields = [
            'id', 'job_posting', 'resume', 'job_posting_title', 'resume_title', 'job_posting_corp_id',
            'positive_feedback', 'negative_feedback', 'enhancements_feedback', 'question', 'answer', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WorkExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkExperience
        fields = ['organization', 'details']

class ProjectExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectExperience
        fields = ['project_name', 'context', 'details']