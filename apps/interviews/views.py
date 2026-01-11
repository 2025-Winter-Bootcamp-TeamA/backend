"""
면접 뷰
"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from .models import InterviewQuestion, InterviewPractice, InterviewAnswer
from .serializers import (
    InterviewQuestionSerializer, InterviewPracticeSerializer,
    InterviewPracticeDetailSerializer, InterviewAnswerSerializer
)


class InterviewQuestionListView(generics.ListAPIView):
    """면접 질문 목록"""
    permission_classes = [AllowAny]
    queryset = InterviewQuestion.objects.filter(is_deleted=False)
    serializer_class = InterviewQuestionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['question_type', 'difficulty', 'tech_stack']


class InterviewQuestionDetailView(generics.RetrieveAPIView):
    """면접 질문 상세"""
    permission_classes = [AllowAny]
    queryset = InterviewQuestion.objects.filter(is_deleted=False)
    serializer_class = InterviewQuestionSerializer


class QuestionsByTechView(generics.ListAPIView):
    """기술 스택별 면접 질문"""
    permission_classes = [AllowAny]
    serializer_class = InterviewQuestionSerializer

    def get_queryset(self):
        tech_stack_id = self.kwargs['tech_stack_id']
        return InterviewQuestion.objects.filter(
            tech_stack_id=tech_stack_id,
            is_deleted=False
        )


class GenerateQuestionsView(APIView):
    """AI 기반 면접 질문 생성"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tech_stacks = request.data.get('tech_stacks', [])
        job_posting_id = request.data.get('job_posting_id')

        # TODO: AI 질문 생성 로직 (Celery 태스크로 처리)
        # 현재는 더미 응답 반환
        return Response({
            'questions': [
                {
                    'question': 'Django에서 ORM을 사용하는 이유와 장단점을 설명해주세요.',
                    'type': 'tech',
                    'difficulty': 'medium',
                },
                {
                    'question': '프로젝트에서 겪었던 가장 어려운 기술적 문제와 해결 방법을 설명해주세요.',
                    'type': 'experience',
                    'difficulty': 'hard',
                },
            ],
            'message': '면접 질문이 생성되었습니다.'
        })


class InterviewPracticeListCreateView(generics.ListCreateAPIView):
    """면접 연습 목록 조회 및 시작"""
    permission_classes = [IsAuthenticated]
    serializer_class = InterviewPracticeSerializer

    def get_queryset(self):
        return InterviewPractice.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class InterviewPracticeDetailView(generics.RetrieveAPIView):
    """면접 연습 상세 (답변 포함)"""
    permission_classes = [IsAuthenticated]
    serializer_class = InterviewPracticeDetailSerializer

    def get_queryset(self):
        return InterviewPractice.objects.filter(user=self.request.user)


class SubmitAnswerView(APIView):
    """답변 제출 및 AI 피드백"""
    permission_classes = [IsAuthenticated]

    def post(self, request, practice_id):
        question_id = request.data.get('question_id')
        user_answer = request.data.get('answer')

        if not question_id or not user_answer:
            return Response(
                {'error': '질문 ID와 답변을 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            practice = InterviewPractice.objects.get(
                pk=practice_id,
                user=request.user
            )
        except InterviewPractice.DoesNotExist:
            return Response(
                {'error': '면접 연습을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 답변 저장
        answer = InterviewAnswer.objects.create(
            practice=practice,
            question_id=question_id,
            user_answer=user_answer
        )

        # TODO: AI 피드백 생성 (Celery 태스크로 처리)
        # 현재는 더미 피드백 반환
        answer.ai_feedback = "좋은 답변입니다. 구체적인 예시를 추가하면 더 좋을 것 같습니다."
        answer.score = 80
        answer.save()

        return Response(InterviewAnswerSerializer(answer).data)
