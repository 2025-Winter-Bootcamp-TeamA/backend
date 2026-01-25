"""
트렌드 뷰
"""

from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from .models import TechStack, Category, TechTrend, TechBookmark
from .models import Article
from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from .serializers import (
    TechStackSerializer, CategorySerializer,
    TechTrendSerializer, TechStackByCategorySerializer,
    TechBookmarkListSerializer, TechBookmarkCreateSerializer,
    TechBookmarkCreateResponseSerializer,
    TechStackWithRelationsSerializer,
    ArticleSerializer
)

from apps.jobs.models import JobPosting
from apps.jobs.serializers import JobPostingSerializer

class CategoryJobPostingListView(generics.ListAPIView):
    """
    특정 카테고리에 포함된 기술 스택을 가진 채용 공고 목록 조회
    """
    permission_classes = [AllowAny]
    # apps/jobs/serializers.py에 있는 시리얼라이저를 사용합니다.
    serializer_class = JobPostingSerializer 

    def get_queryset(self):
        category_id = self.kwargs['category_id']

        # 1. 카테고리 존재 및 삭제 여부 확인
        get_object_or_404(Category, id=category_id, is_deleted=False)

        # 2. 해당 카테고리에 속한 기술 스택(TechStack)들을 먼저 찾습니다.
        stacks_in_category = TechStack.objects.filter(
            category_relations__category_id=category_id, 
            is_deleted=False
        )

        # 3. [핵심 수정] 위에서 찾은 스택을 가진 공고를 찾습니다.
        # tech_stacks (중간테이블) -> tech_stack (진짜 기술스택) -> in 필터링
        return JobPosting.objects.select_related('corp').filter(
            tech_stacks__tech_stack__in=stacks_in_category, # 여기에 __tech_stack을 추가했습니다!
            is_deleted=False
        ).distinct().order_by('-id')
    

class CategoryArticleListView(generics.ListAPIView):
    """
    특정 카테고리에 포함된 기술 스택을 가진 게시글 목록 조회
    """
    permission_classes = [AllowAny]
    serializer_class = ArticleSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'view_count', 'id'] # 허용할 정렬 필드
    ordering = ['-id'] # 기본: 최신순

    def get_queryset(self):
        category_id = self.kwargs['category_id']

        # 1. 카테고리 존재 확인
        get_object_or_404(Category, id=category_id, is_deleted=False)

        # 2. 카테고리에 속한 기술스택들
        stacks_in_category = TechStack.objects.filter(
            category_relations__category_id = category_id,
            is_deleted = False
        )

        # 3. 그 기술스택을 가진 게시글 조회
        return Article.objects.filter(
            tech_stacks__tech_stack__in=stacks_in_category,
            is_deleted = False
        ).distinct()
        


class CategoryTechStackListView(generics.ListAPIView):
    """카테고리별 기술 스택 목록"""
    permission_classes = [AllowAny] # 모든 사용자 접근 허용
    serializer_class = TechStackByCategorySerializer # 시리얼라이저 지정

    def get_queryset(self): # API가 반환할 쿼리셋 정의
        return TechStack.objects.filter(
            category_relations__category_id=self.kwargs['category_id'],
            is_deleted=False
        ) # URL에서 받은 category_id에 속하는 기술과 삭제되지 않은 기술 스택 필터링

    def get_serializer_context(self): # 시리얼라이저 컨텍스트 오버라이드
        context = super().get_serializer_context() # 기본 컨텍스트 가져오기
        context['category_id'] = self.kwargs.get('category_id') # context에 category_id 추가
        return context

    # list 메서드 오버라이드
    def list(self, request, *args, **kwargs): 
        get_object_or_404(Category, pk=self.kwargs['category_id'], is_deleted=False) #url에서 받은 category_id 값을 가져옴, kwargs는 딕셔너리 형태
        # 유효성 검사 후 리스트 반환(삭제되었거나, 존재하지 않으면 404 에러 발생)
        return super().list(request, *args, **kwargs) # get_queryset 메소드로 얻은 쿼리셋을 직렬화 하여 HTTP 응답 


class TechStackListView(generics.ListAPIView):
    """
    기술 스택 목록 조회 API
    - GET /tech-stacks: 기술 스택 목록 조회 (검색 및 필터링 지원)
    """
    permission_classes = [AllowAny]
    queryset = TechStack.objects.filter(is_deleted=False)
    serializer_class = TechStackSerializer
    # 이름만 부분 일치 검색 + exact 필터 병행
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['name']
    search_fields = ['name']  # 기술 스택 이름으로 부분 일치 검색 가능 (icontains 자동 적용)

    @swagger_auto_schema(
        operation_summary='기술 스택 목록 조회',
        operation_description='기술 스택 목록을 조회합니다. '
                              '검색 파라미터(search)를 사용하여 기술 스택 이름으로 부분 일치 검색이 가능합니다. '
                              '필터 파라미터(name)를 사용하여 정확한 이름으로 필터링할 수 있습니다.',
        responses={
            200: TechStackSerializer(many=True),
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class TechStackDetailView(generics.RetrieveAPIView):
    """기술 스택 상세"""
    permission_classes = [AllowAny]
    queryset = TechStack.objects.filter(is_deleted=False)
    serializer_class = TechStackSerializer


class TechDocsURLView(APIView):
    """기술 스택 공식 문서 URL 조회"""
    permission_classes = [AllowAny]

    def get(self, request, tech_stack_id):
        # is_deleted=False 조건으로 삭제되지 않은 객체만 조회, 없으면 404 에러
        tech_stack = get_object_or_404(TechStack, pk=tech_stack_id, is_deleted=False)

        return Response({'docs_url': tech_stack.docs_url})


class CategoryListView(generics.ListAPIView):
    """카테고리 목록"""
    permission_classes = [AllowAny]
    queryset = Category.objects.filter(is_deleted=False)
    serializer_class = CategorySerializer


# class TechTrendListView(generics.ListAPIView):
#     """기술 트렌드 목록
#         요청 예시: GET /api/trends/?tech_stack=1&ordering=reference_date
#     """
#     permission_classes = [AllowAny]
#     queryset = TechTrend.objects.filter(is_deleted=False)
#     serializer_class = TechTrendSerializer
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['tech_stack', 'reference_date']

# class TrendRankingView(APIView):
#     """트렌드 랭킹 조회"""
#     permission_classes = [AllowAny]

#     def get(self, request):
#         # 최근 트렌드 기준 상위 10개
#         trends = TechTrend.objects.filter(
#             is_deleted=False
#         ).order_by('-reference_date', '-mention_count')[:10]

#         serializer = TechTrendSerializer(trends, many=True)
#         return Response(serializer.data)
class TechTrendListView(generics.ListAPIView):
    """
    기술 트렌드 목록 (그래프 데이터용)
    요청 예시: GET /api/trends/?tech_stack=1&ordering=reference_date
    """
    permission_classes = [AllowAny]
    serializer_class = TechTrendSerializer
    
    # [필터 설정]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter] # OrderingFilter 추가
    filterset_fields = ['tech_stack', 'reference_date']
    
    # [정렬 설정] 기본적으로 날짜 오름차순 (과거->현재)
    ordering_fields = ['reference_date', 'job_mention_count']
    ordering = ['reference_date'] 

    def get_queryset(self):
        # [최적화] select_related를 써야 기술 스택 정보를 가져올 때 DB를 1번만 조회합니다.
        # (없으면 데이터 100개일 때 쿼리가 101번 나가는 N+1 문제 발생)
        queryset = TechTrend.objects.select_related('tech_stack').filter(is_deleted=False)
        
        # [선택 사항] "최근 30일" 데이터만 기본으로 보여주고 싶다면?
        # days = self.request.query_params.get('days')
        # if days:
        #     start_date = timezone.now().date() - timedelta(days=int(days))
        #     queryset = queryset.filter(reference_date__gte=start_date)
            
        return queryset
class TrendRankingView(APIView):
    """
    실시간 트렌드 랭킹 조회 (TOP 10)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # [최적화] 여기도 select_related('tech_stack') 필수!
        trends = TechTrend.objects.select_related('tech_stack').filter(
            is_deleted=False
        ).order_by('-reference_date', '-job_mention_count')[:10]

        serializer = TechTrendSerializer(trends, many=True)
        return Response(serializer.data)

class TechBookmarkListCreateAPIView(APIView):
    """
    기술 즐겨찾기 목록 조회 및 생성 API
    - GET /tech-bookmarks: 즐겨찾기 기술 목록 조회
    - POST /tech-bookmarks: 즐겨찾기 기술 추가
    """
    permission_classes = [IsAuthenticated]


    def get(self, request):
        bookmarks = TechBookmark.objects.filter(user=request.user).order_by('-created_at')
        serializer = TechBookmarkListSerializer(bookmarks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=TechBookmarkCreateSerializer)
    def post(self, request):
        serializer = TechBookmarkCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        tech_id = serializer.validated_data.get('tech_id')
        tech_stack = get_object_or_404(TechStack, id=tech_id)
        
        tech_bookmark = TechBookmark.objects.create(user=request.user, tech_stack=tech_stack)

        response_serializer = TechBookmarkCreateResponseSerializer({
            'tech_bookmark_id': tech_bookmark.id,
            'tech_stack_id': tech_bookmark.tech_stack.id,
            'message': "즐겨찾기에 추가되었습니다."
        })
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class TechBookmarkDeleteAPIView(APIView):
    """
    기술 즐겨찾기 삭제 API
    - DELETE /tech-bookmarks/{tech_bookmark_id}: 즐겨찾기 기술 삭제
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, tech_bookmark_id):
        bookmark = get_object_or_404(TechBookmark, id=tech_bookmark_id, user=request.user)
        bookmark.delete()
        return Response({'message': '즐겨찾기가 해제 되었습니다.'}, status=status.HTTP_200_OK)


class TechStackRelationsView(generics.RetrieveAPIView):
    """
    기술 스택의 관련 기술 스택 조회 API
    - GET /tech-stacks/{tech_stack_id}/relations: 특정 기술 스택과 관련된 모든 기술 스택 조회
    """
    permission_classes = [AllowAny]
    queryset = TechStack.objects.filter(is_deleted=False)
    serializer_class = TechStackWithRelationsSerializer
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary='기술 스택 관계 조회',
        operation_description='특정 기술 스택과 관련된 모든 기술 스택을 관계 유형별로 조회합니다. '
                              '시너지 관계, 필수 인프라, 대체 기술, 부모/자식 기술 등을 포함합니다.',
        responses={
            200: TechStackWithRelationsSerializer,
            404: '기술 스택을 찾을 수 없음'
        }
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)