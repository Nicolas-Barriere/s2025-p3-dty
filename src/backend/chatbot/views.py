"""
Albert chatbot integration views.

This module provides the core API endpoints for the chatbot functionality.
"""

import logging
import json
from typing import Dict, Any

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .chatbot import get_chatbot
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
