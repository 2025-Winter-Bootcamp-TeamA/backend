"""
트렌드 시리얼라이저
"""

from rest_framework import serializers
from .models import TechStack, Category, TechTrend, TechBookmark


class TechStackSerializer(serializers.ModelSerializer):
    """기술 스택 시리얼라이저"""

    class Meta:
        model = TechStack
        fields = ['id', 'name', 'logo', 'docs_url', 'created_at']


class CategorySerializer(serializers.ModelSerializer):
    """카테고리 시리얼라이저"""

    class Meta:
        model = Category
        fields = ['id', 'name']


class TechTrendSerializer(serializers.ModelSerializer):
    """기술 트렌드 시리얼라이저"""
    tech_stack = TechStackSerializer(read_only=True)

    class Meta:
        model = TechTrend
        fields = [
            'id', 'tech_stack', 'trend_from',
            'mention_count', 'change_rate', 'reference_date'
        ]


class TechStackByCategorySerializer(serializers.ModelSerializer):
    """카테고리별 기술 스택을 위한 시리얼라이저"""
    category_id = serializers.SerializerMethodField()

    class Meta:
        model = TechStack
        fields = ['name', 'category_id']

    def get_category_id(self, obj):
        return self.context.get('category_id') # 카테고리 ID를 컨텍스트로 가져옴

class TechStackForBookmarkSerializer(serializers.ModelSerializer):
    """즐겨찾기 목록 조회 시 중첩될 기술 스택 시리얼라이저"""
    tech_stack_id = serializers.IntegerField(source='id')
    tech_name = serializers.CharField(source='name')
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = TechStack
        fields = ['tech_stack_id', 'tech_name', 'logo', 'docs_url', 'category_name']

    def get_category_name(self, obj):
        return [relation.category.name for relation in obj.category_relations.all()]


class TechBookmarkListSerializer(serializers.ModelSerializer):
    """기술 즐겨찾기 목록 조회 시리얼라이저"""
    tech_bookmark_id = serializers.IntegerField(source='id')
    tech_stack = TechStackForBookmarkSerializer()

    class Meta:
        model = TechBookmark
        fields = ['tech_bookmark_id', 'created_at', 'tech_stack']


class TechBookmarkCreateSerializer(serializers.ModelSerializer):
    """기술 즐겨찾기 생성용 시리얼라이저"""
    tech_id = serializers.IntegerField(write_only=True, help_text="기술 스택 ID")

    class Meta:
        model = TechBookmark
        fields = ['tech_id']

    def validate_tech_id(self, value):
        if not TechStack.objects.filter(id=value).exists():
            raise serializers.ValidationError("해당 기술 스택을 찾을 수 없습니다.")
        return value

    def validate(self, data):
        user = self.context['request'].user
        tech_id = data.get('tech_id')
        if TechBookmark.objects.filter(user=user, tech_stack_id=tech_id).exists():
            raise serializers.ValidationError("이미 즐겨찾기에 추가된 기술 스택입니다.")
        return data


class TechBookmarkCreateResponseSerializer(serializers.Serializer):
    """기술 즐겨찾기 생성 응답 시리얼라이저"""
    tech_bookmark_id = serializers.IntegerField()
    tech_stack_id = serializers.IntegerField()
    message = serializers.CharField()