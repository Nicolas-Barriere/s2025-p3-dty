"""
Albert chatbot integration views.

This module provides the core API endpoints for the chatbot functionality.
"""

import logging
from typing import Dict, Any

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .chatbot import get_chatbot
from .rag import RAGSystem

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def intelligent_search_api(request):
    """
    Intelligent email search endpoint using Albert API.
    
    This endpoint analyzes the user's first 500 emails and returns
    the best matches using AI-powered search.
    
    POST data:
    {
        "query": "User's natural language search query"
    }
    
    Returns:
    {
        "success": true,
        "results": [...],
        "search_summary": "...",
        "total_matches": 5,
        "total_emails": 500,
        "query": "original query"
    }
    """
    try:
        data = request.data
        query = data.get('query', '').strip()
        
        if not query:
            return Response({
                'success': False,
                'error': 'query is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user ID from authenticated user
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return Response({
                'success': False,
                'error': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        user_id = str(request.user.id)
        logger.info(f"Processing intelligent search for user {user_id}: {query}")
        
        # Use the email service directly for intelligent search
        from .email_service import email_service
        from .api_client import AlbertAPIClient
        from .config import AlbertConfig
        
        # Initialize API client
        config = AlbertConfig()
        api_client = AlbertAPIClient(config)
        
        # Perform intelligent search
        search_results = email_service.chatbot_intelligent_email_search(
            user_id=user_id,
            user_query=query,
            api_client=api_client,
            max_results=10
        )
        
        # Format result for consistency
        if search_results['success']:
            results = search_results.get('results', [])
            logger.info(f"Found {len(results)} matches for query: {query}")
            
            result = {
                'success': True,
                'response': f"Found {len(results)} relevant emails",
                'search_summary': f"AI search found {len(results)} relevant emails from {search_results.get('total_searched', 0)} searched",
                'type': 'intelligent_search',
                'results': results,
                'total_matches': len(results),
                'total_emails': search_results.get('total_searched', 0),
                'original_request': query
            }
        else:
            logger.warning(f"Intelligent search failed: {search_results.get('error', 'Unknown error')}")
            result = {
                'success': False,
                'response': search_results.get('error', 'Search failed'),
                'message': search_results.get('error', 'Search failed'),
                'type': 'intelligent_search',
                'results': [],
                'original_request': query
            }
        
        if result.get('success'):
            return Response({
                'success': True,
                'results': result.get('results', []),
                'search_summary': result.get('search_summary', result.get('response', '')),
                'total_matches': result.get('total_matches', 0),
                'total_emails': result.get('total_emails', 0),
                'query': query,
                'type': 'intelligent_search'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': result.get('response', result.get('message', 'Search failed')),
                'query': query
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        logger.error(f"Error in intelligent_search_api: {e}")
        return Response({
            'success': False,
            'error': f'Search error: {str(e)}',
            'query': query if 'query' in locals() else ''
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chatbot_status_api(request):
    """
    Get chatbot status and configuration.
    
    Returns basic information about the chatbot system.
    """
    try:
        user_id = str(request.user.id) if request.user.is_authenticated else "anonymous"
        
        return Response({
            'success': True,
            'status': 'active',
            'features': {
                'intelligent_search': True,
                'email_analysis': True
            },
            'user_id': user_id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in chatbot_status_api: {e}")
        return Response({
            'success': False,
            'status': 'error',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conversation_api(request):
    """
    General conversation endpoint for chatbot interactions.
    
    This endpoint handles general conversation, email analysis, 
    summarization, and other non-search related tasks.
    
    POST data:
    {
        "message": "User's message",
        "conversation_history": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]
    }
    
    Returns:
    {
        "success": true,
        "response": "Bot response",
        "type": "conversation|email_summary|email_reply|function_call",
        "function_used": "name_of_function_if_any"
    }
    """
    try:
        data = request.data
        message = data.get('message', '').strip()
        conversation_history = data.get('conversation_history', [])
        
        if not message:
            return Response({
                'success': False,
                'error': 'message is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user ID from authenticated user
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return Response({
                'success': False,
                'error': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        user_id = str(request.user.id)
        logger.info(f"Processing conversation for user {user_id}: {message}")
        
        # For general conversation, redirect to intelligent search
        # Since we've simplified the chatbot to only do intelligent search
        logger.info(f"Redirecting conversation to intelligent search for user {user_id}: {message}")
        
        # Use the email service directly for intelligent search
        from .email_service import email_service
        from .api_client import AlbertAPIClient
        from .config import AlbertConfig
        
        # Initialize API client
        config = AlbertConfig()
        api_client = AlbertAPIClient(config)
        
        # Perform intelligent search
        search_results = email_service.chatbot_intelligent_email_search(
            user_id=user_id,
            user_query=message,
            api_client=api_client,
            max_results=10
        )
        
        # Format result for conversation context
        if search_results['success']:
            results = search_results.get('results', [])
            result = {
                'success': True,
                'response': f"Found {len(results)} relevant emails for your query: {message}",
                'type': 'intelligent_search',
                'function_used': 'intelligent_email_search',
                'results': results
            }
        else:
            result = {
                'success': False,
                'response': f"Could not search emails: {search_results.get('error', 'Search failed')}",
                'type': 'error'
            }
        
        if result.get('success'):
            return Response({
                'success': True,
                'response': result.get('response', ''),
                'type': result.get('type', 'conversation'),
                'function_used': result.get('function_used', ''),
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': result.get('response', 'Conversation failed'),
                'type': 'error'
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        logger.error(f"Error in conversation_api: {e}")
        return Response({
            'success': False,
            'error': f'Conversation error: {str(e)}',
            'type': 'error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

