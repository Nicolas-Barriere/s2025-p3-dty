"""
Example Django views for integrating the Albert chatbot functionality.

These views demonstrate how to use the chatbot in a Django REST API.
"""

import logging
from typing import Dict, Any

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import json

from .chatbot import get_chatbot, AlbertChatbot


logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class ChatbotAPIView(View):
    """
    Base view for chatbot operations.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chatbot = get_chatbot()

    def post(self, request, *args, **kwargs):
        """Handle POST requests for chatbot operations."""
        try:
            data = json.loads(request.body)
            operation = data.get('operation')
            
            if operation == 'summarize':
                return self._handle_summarize(data)
            elif operation == 'answer':
                return self._handle_answer(data)
            elif operation == 'classify':
                return self._handle_classify(data)
            elif operation == 'batch':
                return self._handle_batch(data)
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Unknown operation: {operation}'
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in chatbot API: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Internal server error'
            }, status=500)

    def _handle_summarize(self, data: Dict[str, Any]) -> JsonResponse:
        """Handle mail summarization requests."""
        mail_content = data.get('mail_content', '')
        sender = data.get('sender', '')
        subject = data.get('subject', '')
        
        if not mail_content:
            return JsonResponse({
                'success': False,
                'error': 'mail_content is required'
            }, status=400)
        
        result = self.chatbot.summarize_mail(mail_content, sender, subject)
        return JsonResponse(result)

    def _handle_answer(self, data: Dict[str, Any]) -> JsonResponse:
        """Handle mail answer generation requests."""
        original_mail = data.get('original_mail', '')
        context = data.get('context', '')
        tone = data.get('tone', 'professional')
        language = data.get('language', 'french')
        
        if not original_mail:
            return JsonResponse({
                'success': False,
                'error': 'original_mail is required'
            }, status=400)
        
        result = self.chatbot.generate_mail_answer(
            original_mail, context, tone, language
        )
        return JsonResponse(result)

    def _handle_classify(self, data: Dict[str, Any]) -> JsonResponse:
        """Handle mail classification requests."""
        mail_content = data.get('mail_content', '')
        sender = data.get('sender', '')
        subject = data.get('subject', '')
        custom_categories = data.get('custom_categories')
        
        if not mail_content:
            return JsonResponse({
                'success': False,
                'error': 'mail_content is required'
            }, status=400)
        
        result = self.chatbot.classify_mail(
            mail_content, sender, subject, custom_categories
        )
        return JsonResponse(result)

    def _handle_batch(self, data: Dict[str, Any]) -> JsonResponse:
        """Handle batch processing requests."""
        mails = data.get('mails', [])
        operation = data.get('batch_operation', 'summarize')
        
        if not mails:
            return JsonResponse({
                'success': False,
                'error': 'mails list is required for batch operations'
            }, status=400)
        
        results = self.chatbot.process_mail_batch(mails, operation)
        return JsonResponse({
            'success': True,
            'results': results,
            'total_processed': len(results)
        })


# DRF API Views
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def summarize_mail_api(request):
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_answer_api(request):
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def classify_mail_api(request):
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_process_api(request):
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


# Health check endpoint
@api_view(['GET'])
def chatbot_health_check(request):
    """
    Health check endpoint for the chatbot service.
    """
    try:
        chatbot = get_chatbot()
        
        # Test with a simple dummy operation
        test_result = chatbot.summarize_mail(
            "Test email for health check",
            "health@check.com",
            "Health Check"
        )
        
        return Response({
            'status': 'healthy',
            'service': 'albert-chatbot',
            'api_accessible': test_result.get('success', False),
            'timestamp': '2025-06-19T00:00:00Z'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Chatbot health check failed: {e}")
        return Response({
            'status': 'unhealthy',
            'service': 'albert-chatbot',
            'error': str(e),
            'timestamp': '2025-06-19T00:00:00Z'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


# Simple chat endpoint for frontend integration
@api_view(['POST'])
@csrf_exempt
def simple_chat_api(request):
    """
    Simple chat endpoint that accepts a message and returns a response.
    
    POST data:
    {
        "message": "User's message"
    }
    """
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
            
        message = data.get('message', '')
        
        if not message:
            return JsonResponse({
                'success': False,
                'error': 'message is required'
            }, status=400)
        
        # For now, use the summarize function as a simple response generator
        # We can enhance this later to be more conversational
        chatbot = get_chatbot()
        result = chatbot.summarize_mail(
            message, 
            "user@frontend.com", 
            "Chat message"
        )
        
        if result.get('success'):
            # The result contains a summary field which might be nested
            summary_data = result.get('summary', '')
            if isinstance(summary_data, dict):
                response_text = summary_data.get('summary', 'Je vous ai bien compris.')
            else:
                response_text = summary_data or 'Je vous ai bien compris.'
            
            return JsonResponse({
                'success': True,
                'response': response_text
            })
        else:
            return JsonResponse({
                'success': True,
                'response': 'Je suis désolé, je n\'ai pas pu traiter votre message.'
            })
            
    except Exception as e:
        logger.error(f"Error in simple_chat_api: {e}")
        return JsonResponse({
            'success': True,
            'response': 'Une erreur s\'est produite lors du traitement de votre message.'
        })
