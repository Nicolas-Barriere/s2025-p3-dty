"""
Email retrieval functions for the chatbot integration.

This module provides functions to retrieve emails from the mailbox application
database for processing by the chatbot. All functions use core Django models
and relationships directly for security, performance, and maintainability,
avoiding API viewset patterns.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from core import models
from core.enums import ThreadAccessRoleChoices, MailboxRoleChoices, MessageRecipientTypeChoices
from core.search import search_threads

logger = logging.getLogger(__name__)
User = get_user_model()


def get_user_accessible_mailboxes(user_id: str) -> List[models.Mailbox]:
    """
    Get all mailboxes that a user has access to.
    Uses model relationships for better performance.
    
    Args:
        user_id: UUID of the user
        
    Returns:
        List of Mailbox objects the user can access
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Use the user's mailbox_accesses relationship to get accessible mailboxes
        mailboxes = models.Mailbox.objects.filter(
            accesses__user=user
        ).select_related('domain', 'contact').order_by("-created_at")
        
        logger.info(f"Found {mailboxes.count()} accessible mailboxes for user {user}")
        return list(mailboxes)
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
        return []
    except Exception as e:
        logger.error(f"Error retrieving mailboxes for user {user_id}: {e}")
        return []


def get_mailbox_threads(
    mailbox_id: str, 
    user_id: str,
    limit: int = 50,
    filters: Optional[Dict[str, Any]] = None
) -> List[models.Thread]:
    """
    Get threads accessible by a specific mailbox using model methods.
    Uses the mailbox.threads_viewer property for better performance.
    
    Args:
        mailbox_id: UUID of the mailbox
        user_id: UUID of the user (for permission checking)
        limit: Maximum number of threads to return
        filters: Optional filters (has_unread, has_starred, etc.)
        
    Returns:
        List of Thread objects accessible by the mailbox
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Check if user has access to this mailbox using model relationships
        try:
            mailbox = models.Mailbox.objects.get(
                id=mailbox_id, 
                accesses__user=user
            )
        except models.Mailbox.DoesNotExist:
            logger.error(f"User {user_id} does not have access to mailbox {mailbox_id}")
            return []
        
        # Use the mailbox's threads_viewer property from the model
        queryset = mailbox.threads_viewer
        
        # Apply filters if provided using the Thread model's boolean fields
        if filters:
            for field_name, value in filters.items():
                if hasattr(models.Thread, field_name) and isinstance(value, bool):
                    queryset = queryset.filter(**{field_name: value})
        
        # Prefetch related data for better performance 
        threads = queryset.select_related().prefetch_related(
            'messages__sender',
            'messages__recipients__contact',
            'accesses__mailbox'
        ).order_by('-messaged_at', '-created_at')[:limit]
        
        logger.info(f"Found {len(threads)} threads for mailbox {mailbox}")
        return list(threads)
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
        return []
    except models.Mailbox.DoesNotExist:
        logger.error(f"Mailbox with ID {mailbox_id} not found")
        return []
    except Exception as e:
        logger.error(f"Error retrieving threads for mailbox {mailbox_id}: {e}")
        return []


def get_thread_messages(
    thread_id: str, 
    user_id: str,
    include_drafts: bool = False
) -> List[models.Message]:
    """
    Get all messages in a thread using model relationships.
    Uses Thread.messages relationship for better performance.
    
    Args:
        thread_id: UUID of the thread
        user_id: UUID of the user (for permission checking)
        include_drafts: Whether to include draft messages
        
    Returns:
        List of Message objects in the thread
    """
    try:
        user = User.objects.get(id=user_id)
        thread = models.Thread.objects.get(id=thread_id)
        
        # Check if user has access to this thread using ThreadAccess model
        has_access = models.ThreadAccess.objects.filter(
            thread=thread, 
            mailbox__accesses__user=user
        ).exists()
        
        if not has_access:
            logger.error(f"User {user_id} does not have access to thread {thread_id}")
            return []
        
        # Use the thread's messages relationship
        messages_query = thread.messages.select_related(
            'sender', 'thread'
        ).prefetch_related(
            'recipients__contact',
            'attachments__blob'
        ).order_by('created_at')
        
        if not include_drafts:
            messages_query = messages_query.filter(is_draft=False)
        
        messages = list(messages_query)
        logger.info(f"Found {len(messages)} messages in thread {thread}")
        return messages
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
        return []
    except models.Thread.DoesNotExist:
        logger.error(f"Thread with ID {thread_id} not found")
        return []
    except Exception as e:
        logger.error(f"Error retrieving messages for thread {thread_id}: {e}")
        return []


def get_message_by_id(message_id: str, user_id: str) -> Optional[models.Message]:
    """
    Get a specific message by its ID using model relationships.
    Uses ThreadAccess model for permission checking.
    
    Args:
        message_id: UUID of the message
        user_id: UUID of the user (for permission checking)
        
    Returns:
        Message object or None if not found or no access
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Get message and check access through ThreadAccess model
        try:
            message = models.Message.objects.select_related(
                'sender', 'thread'
            ).prefetch_related(
                'recipients__contact',
                'attachments__blob'
            ).get(id=message_id)
            
            # Check if user has access to the thread containing this message
            has_access = models.ThreadAccess.objects.filter(
                thread=message.thread,
                mailbox__accesses__user=user
            ).exists()
            
            if not has_access:
                logger.error(f"User {user_id} does not have access to message {message_id}")
                return None
                
            logger.info(f"Retrieved message: {message}")
            return message
            
        except models.Message.DoesNotExist:
            logger.error(f"Message {message_id} not found")
            return None
            
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error retrieving message {message_id}: {e}")
        return None


def get_parsed_message_content(message: models.Message) -> Dict[str, Any]:
    """
    Get parsed content from a message using the model's built-in parsing methods.
    Uses Message.get_parsed_data() and get_all_recipient_contacts() methods.
    
    Args:
        message: Message object
        
    Returns:
        Dictionary with parsed message content
    """
    try:
        # Use the message's built-in get_parsed_data method
        parsed_data = message.get_parsed_data()
        
        # Extract text and HTML content
        text_body = parsed_data.get('textBody', [])
        html_body = parsed_data.get('htmlBody', [])
        
        # Get attachments using the message's attachments relationship
        attachments = []
        for attachment in message.attachments.all():
            attachments.append({
                'name': attachment.name,
                'size': attachment.size,
                'content_type': attachment.content_type,
                'sha256': attachment.sha256,
            })
        
        # Get recipients using the message's built-in method
        recipients_by_type = message.get_all_recipient_contacts()
        recipients = {
            'to': [{'name': contact.name, 'email': contact.email} 
                   for contact in recipients_by_type.get('to', [])],
            'cc': [{'name': contact.name, 'email': contact.email} 
                   for contact in recipients_by_type.get('cc', [])],
            'bcc': [{'name': contact.name, 'email': contact.email} 
                    for contact in recipients_by_type.get('bcc', [])]
        }
        
        return {
            'subject': message.subject,
            'sender': {
                'name': message.sender.name,
                'email': message.sender.email
            },
            'sent_at': message.sent_at,
            'text_body': text_body,
            'html_body': html_body,
            'attachments': attachments,
            'recipients': recipients,
            'is_draft': message.is_draft,
            'is_unread': message.is_unread,
            'is_starred': message.is_starred,
            'thread_id': str(message.thread.id),
            'message_id': str(message.id),
        }
    except Exception as e:
        logger.error(f"Error parsing message content for {message}: {e}")
        return {
            'subject': message.subject,
            'error': str(e)
        }



def get_message_full_content(message_id: str, user_id: str) -> str:
    """
    Get the full text content of a message for chatbot processing.
    Uses model relationships for permission checking.
    
    Args:
        message_id: UUID of the message
        user_id: UUID of the user (for permission checking)
        
    Returns:
        String containing the full message content
    """
    try:
        message = get_message_by_id(message_id, user_id)
        if not message:
            return ""
        
        parsed_content = get_parsed_message_content(message)
        
        # Combine text content
        content_parts = []
        content_parts.append(f"Subject: {parsed_content['subject']}")
        content_parts.append(f"From: {parsed_content['sender']['name']} <{parsed_content['sender']['email']}>")
        
        # Add recipients
        if parsed_content['recipients']['to']:
            to_list = [f"{r['name']} <{r['email']}>" if r['name'] else r['email'] 
                      for r in parsed_content['recipients']['to']]
            content_parts.append(f"To: {', '.join(to_list)}")
        
        if parsed_content['recipients']['cc']:
            cc_list = [f"{r['name']} <{r['email']}>" if r['name'] else r['email'] 
                      for r in parsed_content['recipients']['cc']]
            content_parts.append(f"CC: {', '.join(cc_list)}")
        
        content_parts.append("")  # Empty line
        
        # Add text body content
        if parsed_content['text_body']:
            for text_part in parsed_content['text_body']:
                if 'content' in text_part:
                    content_parts.append(text_part['content'])
        
        # If no text body, try HTML body (basic extraction)
        elif parsed_content['html_body']:
            for html_part in parsed_content['html_body']:
                if 'content' in html_part:
                    # Basic HTML to text conversion
                    import re
                    html_content = html_part['content']
                    # Remove HTML tags
                    text_content = re.sub(r'<[^>]+>', '', html_content)
                    # Decode HTML entities
                    import html
                    text_content = html.unescape(text_content)
                    content_parts.append(text_content)
        
        # Add attachment info
        if parsed_content['attachments']:
            content_parts.append("")
            content_parts.append("Attachments:")
            for attachment in parsed_content['attachments']:
                content_parts.append(f"- {attachment['name']} ({attachment['size']} bytes)")
        
        full_content = "\n".join(content_parts)
        logger.info(f"Retrieved full content for message {message_id} ({len(full_content)} characters)")
        return full_content
        
    except Exception as e:
        logger.error(f"Error retrieving full content for message {message_id}: {e}")
        return ""
