"""
Email response generator views.

This module provides API endpoints for generating email responses using AI.
"""

import logging
import traceback
from typing import Dict, Any

from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .chatbot import get_chatbot
from .email_writer import create_draft_email
from .email_retrieval import get_message_full_content

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_email_response(request):
    """
    Generate an AI response to an email and create a draft reply.
    
    POST data:
    {
        "message_id": "ID of the message to reply to",
        "mailbox_id": "ID of the mailbox to send from",
        "reply_all": boolean indicating whether to reply to all recipients
    }
    """
    try:
        data = request.data
        
        message_id = data.get('message_id')
        mailbox_id = data.get('mailbox_id')
        reply_all = data.get('reply_all', False)
        
        if not message_id or not mailbox_id:
            return Response({
                'success': False,
                'error': 'message_id and mailbox_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user ID from authenticated user
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return Response({
                'success': False,
                'error': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        user_id = str(request.user.id)
        logger.info(f"Generating email response for message {message_id} from mailbox {mailbox_id}")
        
        # Get the original message content
        message_content = get_message_full_content(message_id)
        if not message_content:
            return Response({
                'success': False,
                'error': 'Message not found or content could not be retrieved'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Use the chatbot to generate a response
        chatbot = get_chatbot()
        
        # Create a prompt for the chatbot that asks it to generate a response to the email
        prompt = f"""
        Tu dois générer une réponse professionnelle et concise à cet email. 
        Utilise un ton formel et adapté à un échange professionnel.
        Ne réponds qu'aux points essentiels de l'email.
        La réponse doit être en français et doit suivre les conventions d'un email professionnel.
        
        CONTENU DE L'EMAIL ORIGINAL:
        
        Sujet: {message_content.get('subject', '(Pas de sujet)')}
        
        De: {message_content.get('sender', {}).get('name', '')} <{message_content.get('sender', {}).get('email', '')}>
        
        {message_content.get('text_body', message_content.get('html_body', '(Contenu vide)'))}
        """
        
        # Get the response from the chatbot
        logger.info(f"Generating response for message with subject: {message_content.get('subject', '(No subject)')}")
        result = chatbot.process_user_message(prompt, user_id, [])
        
        if not result.get('success'):
            logger.error(f"Failed to generate response: {result.get('error')}")
            return Response({
                'success': False,
                'error': result.get('error', 'Failed to generate response')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        generated_response = result.get('response', '')
        logger.info(f"Response generated successfully ({len(generated_response)} characters)")
        
        # Extract recipients based on reply_all flag
        recipients_to = []
        recipients_cc = []
        
        # Always add original sender to recipients
        if message_content.get('sender'):
            recipients_to.append({
                'email': message_content['sender'].get('email', ''),
                'name': message_content['sender'].get('name', '')
            })
        
        # Add CC if reply_all is True
        if reply_all:
            for recipient in message_content.get('to', []):
                if recipient.get('email'):
                    recipients_to.append({
                        'email': recipient.get('email', ''),
                        'name': recipient.get('name', '')
                    })
            
            for recipient in message_content.get('cc', []):
                if recipient.get('email'):
                    recipients_cc.append({
                        'email': recipient.get('email', ''),
                        'name': recipient.get('name', '')
                    })
        
        # Create the draft email
        subject = message_content.get('subject', '')
        if not subject.lower().startswith('re:'):
            subject = f"RE: {subject}"
        
        draft_result = create_draft_email(
            user_id=user_id,
            mailbox_id=mailbox_id,
            subject=subject,
            body=generated_response,
            recipients_to=recipients_to,
            recipients_cc=recipients_cc,
            parent_message_id=message_id,
            thread_id=message_content.get('thread_id')
        )
        
        return Response({
            'success': True,
            'message': 'Response draft created successfully',
            'draft_id': draft_result.get('message_id'),
            'thread_id': draft_result.get('thread_id')
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in generate_email_response: {e}")
        logger.error(traceback.format_exc())
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
