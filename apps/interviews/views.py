"""
면접 뷰
ERD에 면접 관련 테이블이 없으므로, ResumeMatching의 question 필드를 활용
"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.resumes.models import ResumeMatching
from apps.resumes.serializers import ResumeMatchingSerializer


class InterviewQuestionView(APIView):
    """면접 질문 조회 (ResumeMatching의 question 필드 활용)"""
    permission_classes = [IsAuthenticated]

    def get(self, request, matching_id):
        try:
            matching = ResumeMatching.objects.get(
                pk=matching_id,
                resume__user=request.user,
                is_deleted=False
            )
        except ResumeMatching.DoesNotExist:
            return Response(
                {'error': '매칭 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            'matching_id': matching.id,
            'question': matching.question,
            'job_posting': {
                'id': matching.job_posting.id,
                'title': matching.job_posting.title,
            },
            'resume': {
                'id': matching.resume.id,
                'title': matching.resume.title,
            }
        })


class SubmitInterviewAnswerView(APIView):
    """면접 답변 제출 및 피드백 업데이트"""
    permission_classes = [IsAuthenticated]

    def post(self, request, matching_id):
        user_answer = request.data.get('answer')

        if not user_answer:
            return Response(
                {'error': '답변을 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            matching = ResumeMatching.objects.get(
                pk=matching_id,
                resume__user=request.user,
                is_deleted=False
            )
        except ResumeMatching.DoesNotExist:
            return Response(
                {'error': '매칭 정보를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
        )

        # TODO: AI 피드백 생성 (Celery 태스크로 처리)
        # 현재는 더미 피드백으로 feedback 업데이트
        matching.feedback = f"면접 답변: {user_answer}\n\n좋은 답변입니다. 구체적인 예시를 추가하면 더 좋을 것 같습니다."
        matching.save()

        return Response(ResumeMatchingSerializer(matching).data)
