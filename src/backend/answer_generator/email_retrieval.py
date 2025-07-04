"""
Simplified email retrieval functions.

This module provides functions to retrieve email content needed for generating responses.
"""

import logging
import json
import re
from typing import Dict, Any, Optional

from core import models
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()

def clean_html(html_content: str) -> str:
    """
    Simple function to clean HTML from email content.
    
    Args:
        html_content: HTML content to clean
        
    Returns:
        Plain text version of the content
    """
    if not html_content:
        return ""
        
    # Remove problematic elements that might cause issues
    # Remove script tags and their content
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove style tags and their content
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove images with cid: sources (inline attachments) as they cause CSP violations
    text = re.sub(r'<img[^>]*src=["\']cid:[^"\']*["\'][^>]*>', '[Image removed]', text, flags=re.IGNORECASE)
    
    # Remove all remaining HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # Remove multiple spaces and newlines
    text = re.sub(r'\s+', ' ', text)
    
    # Decode common HTML entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&apos;', "'")
    
    return text.strip()

def get_message_full_content(message_id: str) -> Dict[str, Any]:
    """
    Get the full content of a message for response generation.
    
    Args:
        message_id: UUID of the message
        
    Returns:
        Dictionary containing the message content
    """
    try:
        # Retrieve message from database
        message = models.Message.objects.get(id=message_id)
        
        # Get sender information
        sender = {
            'email': message.sender.email,
            'name': message.sender.name
        }
        
        # Get recipients
        to_recipients = []
        cc_recipients = []
        
        for recipient in message.recipients.all():
            recipient_data = {
                'email': recipient.contact.email,
                'name': recipient.contact.name
            }
            
            if recipient.type == 'to':
                to_recipients.append(recipient_data)
            elif recipient.type == 'cc':
                cc_recipients.append(recipient_data)
        
        # Get message body content
        text_body = ""
        html_body = ""
        
        # If we have draft body JSON, parse it first
        if message.is_draft and message.draft_body:
            try:
                draft_data = json.loads(message.draft_body)
                if 'content' in draft_data:
                    text_body = draft_data['content']
            except (json.JSONDecodeError, KeyError):
                pass
        
        # If no draft body, try to get content from parsed email data
        if not text_body:
            parsed_data = message.get_parsed_data()
            if parsed_data:
                # Try to get text content
                text_body = parsed_data.get('text_body', '')
                # Try to get HTML content if no text
                if not text_body:
                    html_body = parsed_data.get('html_body', '')
                    if html_body:
                        text_body = clean_html(html_body)
        
        # If we have HTML but no text, convert HTML to text
        if not text_body and html_body:
            text_body = clean_html(html_body)
        
        return {
            'message_id': str(message.id),
            'thread_id': str(message.thread_id),
            'subject': message.subject,
            'sender': sender,
            'to': to_recipients,
            'cc': cc_recipients,
            'text_body': text_body,
            'html_body': html_body,
            'is_draft': message.is_draft,
            'sent_at': message.sent_at.isoformat() if message.sent_at else None
        }
        
    except models.Message.DoesNotExist:
        logger.error(f"Message not found: {message_id}")
        return {}
    except Exception as e:
        logger.error(f"Error retrieving message content: {e}")
        return {}
