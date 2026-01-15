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


class TechBookmarkSerializer(serializers.ModelSerializer):
    """기술 즐겨찾기 시리얼라이저"""
    tech_stack = TechStackSerializer(read_only=True)

    class Meta:
        model = TechBookmark
        fields = ['id', 'tech_stack', 'created_at']


class TechStackByCategorySerializer(serializers.ModelSerializer):
    """카테고리별 기술 스택을 위한 시리얼라이저"""
    category_id = serializers.SerializerMethodField()

    class Meta:
        model = TechStack
        fields = ['name', 'category_id']

    def get_category_id(self, obj):
        return self.context.get('category_id') # 카테고리 ID를 컨텍스트로 가져옴
