"""
면접 시리얼라이저
"""

from rest_framework import serializers
from apps.trends.serializers import TechStackSerializer
from .models import InterviewQuestion, InterviewPractice, InterviewAnswer


class InterviewQuestionSerializer(serializers.ModelSerializer):
    """면접 질문 시리얼라이저"""
    tech_stack = TechStackSerializer(read_only=True)

    class Meta:
        model = InterviewQuestion
        fields = [
            'id', 'tech_stack', 'question', 'answer_guide',
            'question_type', 'difficulty'
        ]


class InterviewAnswerSerializer(serializers.ModelSerializer):
    """면접 답변 시리얼라이저"""
    question = InterviewQuestionSerializer(read_only=True)

    class Meta:
        model = InterviewAnswer
        fields = [
            'id', 'question', 'user_answer',
            'ai_feedback', 'score', 'created_at'
        ]


class InterviewPracticeSerializer(serializers.ModelSerializer):
    """면접 연습 시리얼라이저"""

    class Meta:
        model = InterviewPractice
        fields = ['id', 'job_posting', 'created_at']
        read_only_fields = ['id', 'created_at']


class InterviewPracticeDetailSerializer(serializers.ModelSerializer):
    """면접 연습 상세 시리얼라이저"""
    answers = InterviewAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = InterviewPractice
        fields = ['id', 'job_posting', 'answers', 'created_at']
