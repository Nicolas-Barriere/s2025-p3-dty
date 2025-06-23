"""
API ViewSet for chatbot
"""

import logging
from typing import Dict, Any

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.parsers import JSONParser


import json

from .. import permissions
from ..serializers import ChatbotInputSerializer, ChatbotAnswerOutputSerializer, ChatbotBatchOutputSerializer, ChatbotSummarizeOutputSerializer, ChatbotClassifyOutputSerializer
from messages.chatbot import get_chatbot, AlbertChatbot


logger = logging.getLogger(__name__)

@extend_schema(tags=["chatbot"])
class ChatbotViewSet(viewsets.ViewSet):
    """
    ViewSet for calls to chatbot
    """
    
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser]


    @extend_schema(
        request=ChatbotInputSerializer,
        responses={200: ChatbotSummarizeOutputSerializer},
        description="""
        Generate a summary of an email using AI.
        
        Requires mail_content as input. Optional sender and subject fields
        can provide additional context for better summarization.
        """,
    )
    @action(detail=False, methods=["post"], url_path="summarize")
    def summarize(self, request):
        """
        API endpoint for mail summarization using DRF.
        
        POST data:
        {
            "mail_content": "Email content to summarize",
            "sender": "sender@example.com",
            "subject": "Email subject"
        }
        """
        try:
            chatbot = get_chatbot()
            
            mail_content = request.data.get('mail_content', '')
            sender = request.data.get('sender', '')
            subject = request.data.get('subject', '')
            
            if not mail_content:
                return Response(
                    {'error': 'mail_content is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"Summarizing mail from {sender}")
            result = chatbot.summarize_mail(mail_content, sender, subject)
            
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error in summarize_mail_api: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        request=ChatbotInputSerializer,
        responses={200: ChatbotAnswerOutputSerializer},
        description="""
        Generate an AI response to an email.
        
        Requires original_mail content. Optional context, tone (professional/friendly/formal),
        and language (french/english) parameters can customize the response style.
        """,
    )
    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        """
        API endpoint for mail answer generation using DRF.
        
        POST data:
        {
            "original_mail": "Original email content",
            "context": "Additional context",
            "tone": "professional|friendly|formal",
            "language": "french|english"
        }
        """
        try:
            chatbot = get_chatbot()
            
            original_mail = request.data.get('original_mail', '')
            context = request.data.get('context', '')
            tone = request.data.get('tone', 'professional')
            language = request.data.get('language', 'french')
            
            if not original_mail:
                return Response(
                    {'error': 'original_mail is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"Generating answer with tone: {tone}")
            result = chatbot.generate_mail_answer(original_mail, context, tone, language)
            
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error in generate_answer_api: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @extend_schema(
        request=ChatbotInputSerializer,
        responses={200: ChatbotClassifyOutputSerializer},
        description="""
        Classify an email into predefined or custom categories using AI.
        
        Requires mail_content as input. Optional custom_categories array can override
        default classification categories. Returns the predicted category and confidence score.
        """,
    )
    @action(detail=False, methods=["post"], url_path="classify")
    def classify(self, request):
        """
        API endpoint for mail classification using DRF.
        
        POST data:
        {
            "mail_content": "Email content to classify",
            "sender": "sender@example.com",
            "subject": "Email subject",
            "custom_categories": ["category1", "category2"]  // optional
        }
        """
        try:
            chatbot = get_chatbot()
            
            mail_content = request.data.get('mail_content', '')
            sender = request.data.get('sender', '')
            subject = request.data.get('subject', '')
            custom_categories = request.data.get('custom_categories')
            
            if not mail_content:
                return Response(
                    {'error': 'mail_content is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"Classifying mail from {sender}")
            result = chatbot.classify_mail(mail_content, sender, subject, custom_categories)
            
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error in classify_mail_api: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @extend_schema(
        request=ChatbotInputSerializer,
        responses={200: ChatbotBatchOutputSerializer},
        description="""
        Process multiple emails in batch using AI operations.
        
        Requires an array of mail objects and an operation type (summarize/classify/answer).
        Each mail object should contain content, sender, and subject fields. Optional
        context and tone fields for answer generation.
        """,
    )
    @action(detail=False, methods=["post"], url_path="batch")
    def batch(self, request):
        """
        API endpoint for batch processing mails using DRF.
        
        POST data:
        {
            "mails": [
                {
                    "content": "Email content",
                    "sender": "sender@example.com",
                    "subject": "Subject",
                    "context": "context for answers",  // optional for answer generation
                    "tone": "professional"  // optional for answer generation
                }
            ],
            "operation": "summarize|classify|answer"
        }
        """
        try:
            chatbot = get_chatbot()
            
            mails = request.data.get('mails', [])
            operation = request.data.get('operation', 'summarize')
            
            if not mails:
                return Response(
                    {'error': 'mails list is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if operation not in ['summarize', 'classify', 'answer']:
                return Response(
                    {'error': 'operation must be one of: summarize, classify, answer'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"Processing batch of {len(mails)} mails for operation: {operation}")
            results = chatbot.process_mail_batch(mails, operation)
            
            return Response({
                'success': True,
                'results': results,
                'total_processed': len(results),
                'operation': operation
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in batch_process_api: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )