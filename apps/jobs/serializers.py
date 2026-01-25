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
        fields = ['id', 'name', 'logo_url', 'address',
                  'region_city', 'region_district',
                  ]

class CorpDetailSerializer(serializers.ModelSerializer):
    """기업 상세 시리얼라이저"""
    #job_posting_count = serializers.SerializerMethodField()

    class Meta:
        model = Corp
        fields = [
            'id', 'name', 'logo_url', 'address',
            'latitude', 'longitude',  'region_city', 'region_district',
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
        fields = ['id', 'corp', 'url', 'title', 'career','min_career', 'max_career',
                   'expiry_date','created_at']


class JobPostingDetailSerializer(serializers.ModelSerializer):
    """채용 공고 상세 시리얼라이저"""
    corp = CorpDetailSerializer(read_only=True)
    tech_stacks = JobPostingStackSerializer(many=True, read_only=True)

    class Meta:
        model = JobPosting
        fields = [
            'id', 'corp', 'url', 'title', 'description',
            #'stack_count',
            'tech_stacks', 'created_at'
        ]
# class CorpBookmarkSerializer(serializers.ModelSerializer):
#     """기업 즐겨찾기 시리얼라이저"""
#     corp = CorpSerializer(read_only=True)

#     class Meta:
#         model = CorpBookmark
#         fields = ['id', 'corp', 'created_at']
class CorpBookmarkListSerializer(serializers.ModelSerializer):
    """
    기업 즐겨찾기 목록 조회 시리얼라이저
    """
    corp_bookmark_id = serializers.IntegerField(source='id')
    # 기업 상세 정보를 포함합니다.
    corp = CorpSerializer(read_only=True)

    class Meta:
        model = CorpBookmark
        fields = ['corp_bookmark_id', 'created_at', 'corp']

class CorpBookmarkCreateSerializer(serializers.ModelSerializer):
    """
    기업 즐겨찾기 생성용 시리얼라이저
    """
    corp_id = serializers.IntegerField(write_only=True, help_text="기업 ID")

    class Meta:
        model = CorpBookmark
        fields = ['corp_id']

    def validate_corp_id(self, value):
        # 해당 기업이 실제로 존재하는지 검증합니다.
        if not Corp.objects.filter(id=value, is_deleted=False).exists():
            raise serializers.ValidationError("해당 기업을 찾을 수 없습니다.")
        return value

    def validate(self, data):
        # 이미 즐겨찾기에 추가했는지 중복 여부를 검증합니다.
        user = self.context['request'].user
        corp_id = data.get('corp_id')
        if CorpBookmark.objects.filter(user=user, corp_id=corp_id).exists():
            raise serializers.ValidationError("이미 즐겨찾기에 추가된 기업입니다.")
        return data
class CorpBookmarkCreateResponseSerializer(serializers.Serializer):
    """
    기업 즐겨찾기 생성 응답 시리얼라이저
    """
    corp_bookmark_id = serializers.IntegerField()
    corp_id = serializers.IntegerField()
    message = serializers.CharField()