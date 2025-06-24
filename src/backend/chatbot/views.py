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
from .email_retrieval import (
    get_user_accessible_mailboxes,
    get_mailbox_threads,
    get_thread_messages,
    get_message_by_id,
    get_parsed_message_content,
    search_messages,
    get_unread_messages,
    get_recent_messages,
    get_message_full_content
)


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
@permission_classes([IsAuthenticated])
def simple_chat_api(request):
    """
    Enhanced chat endpoint that accepts a message and returns an intelligent response.
    
    The endpoint now supports:
    - Intent detection (conversation, email summarization, reply generation, classification)
    - Function calling based on detected intent
    - Conversational responses as default behavior
    
    POST data:
    {
        "message": "User's message",
        "conversation_history": [  // optional
            {"role": "user", "content": "previous message"},
            {"role": "assistant", "content": "previous response"}
        ]
    }
    """
    try:
        # Use DRF's request.data instead of manually parsing JSON
        data = request.data
            
        message = data.get('message', '')
        conversation_history = data.get('conversation_history', [])
        
        if not message:
            return Response({
                'success': False,
                'error': 'message is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user ID from authenticated user only (security: no fallback)
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return Response({
                'success': False,
                'error': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        user_id = str(request.user.id)
        logger.info(f"Processing message for authenticated user: {user_id}")
        
        # Use the enhanced chatbot with intent detection and function calling
        chatbot = get_chatbot()
        result = chatbot.process_user_message(message, user_id, conversation_history)
        
        if result.get('success'):
            return Response({
                'success': True,
                'response': result.get('response', 'Je vous ai bien compris.'),
                'type': result.get('type', 'conversation'),
                'function_used': result.get('function_used'),
                'original_intent': result.get('original_intent')
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': True,
                'response': result.get('response', 'Je suis désolé, je n\'ai pas pu traiter votre message.'),
                'type': 'error',
                'error': result.get('error')
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        logger.error(f"Error in simple_chat_api: {e}")
        return Response({
            'success': True,
            'response': 'Une erreur s\'est produite lors du traitement de votre message.',
            'type': 'error',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def email_retrieval_test_api(request):
    """
    Test endpoint for email retrieval operations.
    Requires authentication for security.
    """
    try:
        # Get query parameters
        test_type = request.GET.get('test', 'basic')
        message_id = request.GET.get('message_id')
        mailbox_id = request.GET.get('mailbox_id')
        
        # Use authenticated user ID for all operations
        user_id = str(request.user.id)
        
        results = {'test_type': test_type, 'success': False}
        
        if test_type == 'basic':
            # Test basic functionality
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            user = request.user
            mailboxes = get_user_accessible_mailboxes(user_id)
            results.update({
                'success': True,
                'user_id': user_id,
                'user_email': str(user),
                'mailboxes_count': len(mailboxes),
                'mailboxes': [str(mb) for mb in mailboxes[:5]]
            })
                
        elif test_type == 'unread':
            # Test unread messages
            unread = get_unread_messages(user_id, limit=10)
            results.update({
                'success': True,
                'user_id': user_id,
                'unread_count': len(unread),
                'unread_messages': unread
            })
            
        elif test_type == 'recent':
            # Test recent messages
            recent = get_recent_messages(user_id, days=7, limit=10)
            results.update({
                'success': True,
                'user_id': user_id,
                'recent_count': len(recent),
                'recent_messages': recent
            })
            
        elif test_type == 'message' and message_id:
            # Test specific message
            message = get_message_by_id(message_id, user_id)
            if message:
                content = get_parsed_message_content(message)
                full_content = get_message_full_content(message_id, user_id)
                results.update({
                    'success': True,
                    'message_found': True,
                    'subject': message.subject,
                    'sender': str(message.sender),
                    'content_preview': content,
                    'full_content_length': len(full_content)
                })
            else:
                results['error'] = f'Message {message_id} not found or access denied'
                
        elif test_type == 'threads' and mailbox_id:
            # Test mailbox threads
            threads = get_mailbox_threads(mailbox_id, user_id, limit=5)
            results.update({
                'success': True,
                'threads_count': len(threads),
                'threads': [{'id': str(t.id), 'subject': t.subject} for t in threads]
            })
            
        elif test_type == 'search':
            # Test search
            query = request.GET.get('q', '')
            search_results = search_messages(user_id, query=query, limit=10)
            results.update({
                'success': True,
                'user_id': user_id,
                'search_query': query,
                'results_count': len(search_results),
                'search_results': search_results
            })
            
        else:
            results['error'] = 'Invalid test type or missing parameters'
        
        return Response(results, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception("Error in email retrieval test")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
