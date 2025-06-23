"""
Email retrieval functions for the chatbot integration.

This module provides functions to retrieve emails from the mailbox application
database for processing by the chatbot.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from django.db.models import Q, Prefetch
from django.contrib.auth import get_user_model

from core import models
from core.enums import ThreadAccessRoleChoices, MailboxRoleChoices, MessageRecipientTypeChoices

logger = logging.getLogger(__name__)
User = get_user_model()


def get_user_accessible_mailboxes(user_id: str) -> List[models.Mailbox]:
    """
    Get all mailboxes that a user has access to.
    
    Args:
        user_id: UUID of the user
        
    Returns:
        List of Mailbox objects the user can access
    """
    try:
        user = User.objects.get(id=user_id)
        mailboxes = models.Mailbox.objects.filter(
            accesses__user=user
        ).select_related('domain').distinct()
        
        logger.info(f"Found {mailboxes.count()} accessible mailboxes for user {user}")
        return list(mailboxes)
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
        return []
    except Exception as e:
        logger.error(f"Error retrieving mailboxes for user {user_id}: {e}")
        return []


def get_mailbox_threads(mailbox_id: str, limit: int = 50) -> List[models.Thread]:
    """
    Get threads accessible by a specific mailbox.
    
    Args:
        mailbox_id: UUID of the mailbox
        limit: Maximum number of threads to return
        
    Returns:
        List of Thread objects accessible by the mailbox
    """
    try:
        mailbox = models.Mailbox.objects.get(id=mailbox_id)
        threads = models.Thread.objects.filter(
            accesses__mailbox=mailbox
        ).select_related().prefetch_related(
            'messages__sender',
            'messages__recipients__contact'
        ).order_by('-messaged_at')[:limit]
        
        logger.info(f"Found {len(threads)} threads for mailbox {mailbox}")
        return list(threads)
    except models.Mailbox.DoesNotExist:
        logger.error(f"Mailbox with ID {mailbox_id} not found")
        return []
    except Exception as e:
        logger.error(f"Error retrieving threads for mailbox {mailbox_id}: {e}")
        return []


def get_thread_messages(thread_id: str, include_drafts: bool = False) -> List[models.Message]:
    """
    Get all messages in a thread.
    
    Args:
        thread_id: UUID of the thread
        include_drafts: Whether to include draft messages
        
    Returns:
        List of Message objects in the thread
    """
    try:
        thread = models.Thread.objects.get(id=thread_id)
        messages_query = thread.messages.select_related('sender').prefetch_related(
            'recipients__contact',
            'attachments__blob'
        ).order_by('created_at')
        
        if not include_drafts:
            messages_query = messages_query.filter(is_draft=False)
        
        messages = list(messages_query)
        logger.info(f"Found {len(messages)} messages in thread {thread}")
        return messages
    except models.Thread.DoesNotExist:
        logger.error(f"Thread with ID {thread_id} not found")
        return []
    except Exception as e:
        logger.error(f"Error retrieving messages for thread {thread_id}: {e}")
        return []


def get_message_by_id(message_id: str) -> Optional[models.Message]:
    """
    Get a specific message by its ID.
    
    Args:
        message_id: UUID of the message
        
    Returns:
        Message object or None if not found
    """
    try:
        message = models.Message.objects.select_related('sender', 'thread').prefetch_related(
            'recipients__contact',
            'attachments__blob'
        ).get(id=message_id)
        
        logger.info(f"Retrieved message: {message}")
        return message
    except models.Message.DoesNotExist:
        logger.error(f"Message with ID {message_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error retrieving message {message_id}: {e}")
        return None


def get_parsed_message_content(message: models.Message) -> Dict[str, Any]:
    """
    Get parsed content from a message including text, HTML, and attachments.
    
    Args:
        message: Message object
        
    Returns:
        Dictionary with parsed message content
    """
    try:
        # Get parsed data from the message's raw MIME
        parsed_data = message.get_parsed_data()
        
        # Extract text and HTML content
        text_body = []
        html_body = []
        
        if 'textBody' in parsed_data:
            text_body = parsed_data['textBody']
        if 'htmlBody' in parsed_data:
            html_body = parsed_data['htmlBody']
        
        # Get attachments
        attachments = []
        for attachment in message.attachments.all():
            attachments.append({
                'name': attachment.name,
                'size': attachment.size,
                'content_type': attachment.content_type,
                'sha256': attachment.sha256,
            })
        
        # Get recipients
        recipients = {
            'to': [],
            'cc': [],
            'bcc': []
        }
        
        for recipient in message.recipients.all():
            recipient_data = {
                'name': recipient.contact.name,
                'email': recipient.contact.email
            }
            recipients[recipient.type].append(recipient_data)
        
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


def search_messages(
    user_id: str,
    query: str = "",
    mailbox_id: Optional[str] = None,
    limit: int = 20,
    include_archived: bool = False
) -> List[Dict[str, Any]]:
    """
    Search for messages based on various criteria.
    
    Args:
        user_id: UUID of the user performing the search
        query: Search query (subject, content, sender)
        mailbox_id: Optional specific mailbox to search in
        limit: Maximum number of results
        include_archived: Whether to include archived messages
        
    Returns:
        List of dictionaries with message information
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Build base query for messages user has access to
        messages_query = models.Message.objects.select_related(
            'sender', 'thread'
        ).prefetch_related(
            'recipients__contact'
        )
        
        # Filter by user's accessible mailboxes
        user_mailboxes = models.Mailbox.objects.filter(accesses__user=user)
        messages_query = messages_query.filter(
            thread__accesses__mailbox__in=user_mailboxes
        )
        
        # Filter by specific mailbox if provided
        if mailbox_id:
            messages_query = messages_query.filter(
                thread__accesses__mailbox_id=mailbox_id
            )
        
        # Apply search query if provided
        if query:
            messages_query = messages_query.filter(
                Q(subject__icontains=query) |
                Q(sender__name__icontains=query) |
                Q(sender__email__icontains=query)
            )
        
        # Filter archived messages
        if not include_archived:
            messages_query = messages_query.filter(is_archived=False)
        
        # Exclude drafts and trashed messages by default
        messages_query = messages_query.filter(
            is_draft=False,
            is_trashed=False
        )
        
        messages = messages_query.distinct().order_by('-created_at')[:limit]
        
        # Convert to simplified format
        results = []
        for message in messages:
            results.append({
                'message_id': str(message.id),
                'thread_id': str(message.thread.id),
                'subject': message.subject,
                'sender_name': message.sender.name,
                'sender_email': message.sender.email,
                'sent_at': message.sent_at,
                'is_unread': message.is_unread,
                'is_starred': message.is_starred,
                'thread_subject': message.thread.subject,
            })
        
        logger.info(f"Found {len(results)} messages for search query: {query}")
        return results
        
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
        return []
    except Exception as e:
        logger.error(f"Error searching messages: {e}")
        return []


def get_unread_messages(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get unread messages for a user.
    
    Args:
        user_id: UUID of the user
        limit: Maximum number of messages to return
        
    Returns:
        List of dictionaries with unread message information
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Get unread messages from user's accessible mailboxes
        user_mailboxes = models.Mailbox.objects.filter(accesses__user=user)
        messages = models.Message.objects.select_related(
            'sender', 'thread'
        ).filter(
            thread__accesses__mailbox__in=user_mailboxes,
            is_unread=True,
            is_draft=False,
            is_trashed=False
        ).order_by('-created_at')[:limit]
        
        results = []
        for message in messages:
            results.append({
                'message_id': str(message.id),
                'thread_id': str(message.thread.id),
                'subject': message.subject,
                'sender_name': message.sender.name,
                'sender_email': message.sender.email,
                'sent_at': message.sent_at,
                'thread_subject': message.thread.subject,
            })
        
        logger.info(f"Found {len(results)} unread messages for user {user}")
        return results
        
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
        return []
    except Exception as e:
        logger.error(f"Error retrieving unread messages: {e}")
        return []


def get_recent_messages(user_id: str, days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get recent messages for a user within the specified number of days.
    
    Args:
        user_id: UUID of the user
        days: Number of days to look back
        limit: Maximum number of messages to return
        
    Returns:
        List of dictionaries with recent message information
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        user = User.objects.get(id=user_id)
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Get recent messages from user's accessible mailboxes
        user_mailboxes = models.Mailbox.objects.filter(accesses__user=user)
        messages = models.Message.objects.select_related(
            'sender', 'thread'
        ).filter(
            thread__accesses__mailbox__in=user_mailboxes,
            created_at__gte=cutoff_date,
            is_draft=False,
            is_trashed=False
        ).order_by('-created_at')[:limit]
        
        results = []
        for message in messages:
            results.append({
                'message_id': str(message.id),
                'thread_id': str(message.thread.id),
                'subject': message.subject,
                'sender_name': message.sender.name,
                'sender_email': message.sender.email,
                'sent_at': message.sent_at,
                'is_unread': message.is_unread,
                'is_starred': message.is_starred,
                'thread_subject': message.thread.subject,
            })
        
        logger.info(f"Found {len(results)} recent messages ({days} days) for user {user}")
        return results
        
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
        return []
    except Exception as e:
        logger.error(f"Error retrieving recent messages: {e}")
        return []


def get_message_full_content(message_id: str) -> str:
    """
    Get the full text content of a message for chatbot processing.
    
    Args:
        message_id: UUID of the message
        
    Returns:
        String containing the full message content
    """
    try:
        message = get_message_by_id(message_id)
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
