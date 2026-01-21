"""
트렌드 시리얼라이저
"""

from rest_framework import serializers
from .models import TechStack, Category, TechTrend, TechBookmark, TechStackRelationship, Article


class TechStackSerializer(serializers.ModelSerializer):
    """기술 스택 시리얼라이저"""

    class Meta:
        model = TechStack
        fields = ['id', 'name', 'description', 'logo', 'docs_url', 'created_at']


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


class RelatedTechStackSerializer(serializers.ModelSerializer):
    """관련 기술 스택 간단 정보 시리얼라이저"""
    class Meta:
        model = TechStack
        fields = ['id', 'name', 'description', 'logo', 'docs_url']


class TechStackWithRelationsSerializer(serializers.ModelSerializer):
    """관계 정보를 포함한 기술 스택 시리얼라이저"""
    relationships = serializers.SerializerMethodField()
    description = serializers.CharField(read_only=True)

    class Meta:
        model = TechStack
        fields = [
            'id', 'name', 'description', 'logo', 'docs_url',
            'relationships', 'created_at'
        ]

    def get_relationships(self, obj):
        """
        중앙 기술 스택(검색 대상)을 기준으로 양방향 관계를 모두 조회
        """
        from .models import TechStackRelationship
        
        # 1. 중앙 기술 → 다른 기술 (outgoing)
        outgoing = TechStackRelationship.objects.filter(
            from_tech_stack=obj,
            is_deleted=False
        ).select_related('to_tech_stack').order_by('-weight', 'to_tech_stack__name')
        
        # 2. 다른 기술 → 중앙 기술 (incoming)
        incoming = TechStackRelationship.objects.filter(
            to_tech_stack=obj,
            is_deleted=False
        ).select_related('from_tech_stack').order_by('-weight', 'from_tech_stack__name')
        
        # 관계 유형별로 그룹화
        grouped = {}
        
        # Outgoing 관계 처리
        for rel in outgoing:
            rel_type = rel.relationship_type
            if rel_type not in grouped:
                grouped[rel_type] = []
            
            grouped[rel_type].append({
                'tech_stack': RelatedTechStackSerializer(rel.to_tech_stack).data,
                'weight': rel.weight,
                'relationship_type_display': rel.get_relationship_type_display(),
                'direction': 'outgoing'
            })
        
        # Incoming 관계 처리 (관계 유형 변환)
        for rel in incoming:
            # incoming 관계를 적절한 유형으로 변환
            if rel.relationship_type == 'parent':
                # 다른 기술이 중앙 기술의 부모 → 중앙 기술은 그 기술의 자식
                rel_type = 'child'
            elif rel.relationship_type == 'child':
                # 다른 기술이 중앙 기술의 자식 → 중앙 기술은 그 기술의 부모
                rel_type = 'parent'
            elif rel.relationship_type in ['synergy_with', 'alternative']:
                # 시너지와 대체는 양방향이므로 그대로
                rel_type = rel.relationship_type
            else:
                # required_infra는 단방향이므로 건너뜀
                continue
            
            if rel_type not in grouped:
                grouped[rel_type] = []
            
            grouped[rel_type].append({
                'tech_stack': RelatedTechStackSerializer(rel.from_tech_stack).data,
                'weight': rel.weight,
                'relationship_type_display': self._get_relationship_display(rel_type),
                'direction': 'incoming'
            })
        
        return grouped
    
    def _get_relationship_display(self, rel_type):
        """관계 유형 한글 표시"""
        displays = {
            'synergy_with': '시너지 관계',
            'required_infra': '필수 인프라',
            'alternative': '대체 기술',
            'parent': '부모 기술',
            'child': '자식 기술',
        }
        return displays.get(rel_type, rel_type)
    

class ArticleSerializer(serializers.ModelSerializer):
    """커뮤니티 게시글(Article) 목록 시리얼라이저"""
    class Meta:
        model = Article
        fields = ['id', 'url', 'source', 'view_count', 'created_at']