"""
Email retrieval functions for the chatbot integration.

This module provides functions to retrieve emails from the mailbox application
database for processing by the chatbot.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from django.db.models import Q, Prefetch, Exists, OuterRef
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
    Enhanced to use existing viewset patterns for better permission checking.
    
    Args:
        user_id: UUID of the user
        
    Returns:
        List of Mailbox objects the user can access
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Use the same pattern as MailboxViewSet.get_queryset()
        accesses = user.mailbox_accesses.all()
        mailboxes = models.Mailbox.objects.filter(
            id__in=accesses.values_list("mailbox_id", flat=True)
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
    Get threads accessible by a specific mailbox with enhanced permission checking.
    Enhanced to use existing viewset patterns and permission checks.
    
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
        
        # Check if user has access to this mailbox (same pattern as ThreadViewSet)
        try:
            mailbox = models.Mailbox.objects.get(id=mailbox_id, accesses__user=user)
        except models.Mailbox.DoesNotExist:
            logger.error(f"User {user_id} does not have access to mailbox {mailbox_id}")
            return []
        
        # Use the mailbox.threads_viewer property like ThreadViewSet does
        queryset = mailbox.threads_viewer
        
        # Apply filters if provided (same pattern as ThreadViewSet)
        if filters:
            filter_mapping = {
                "has_trashed": "has_trashed",
                "has_draft": "has_draft", 
                "has_starred": "has_starred",
                "has_sender": "has_sender",
                "has_active": "has_active",
                "has_messages": "has_messages",
                "is_spam": "is_spam",
            }
            
            for param, filter_field in filter_mapping.items():
                if param in filters:
                    value = filters[param]
                    if value is True:
                        queryset = queryset.filter(**{filter_field: True})
                    elif value is False:
                        queryset = queryset.filter(**{filter_field: False})
        
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
    Get all messages in a thread with enhanced permission checking.
    Enhanced to use existing viewset patterns and permission checks.
    
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
        
        # Check if user has access to this thread (same pattern as MessageViewSet)
        has_access = models.ThreadAccess.objects.filter(
            thread=thread, mailbox__accesses__user=user
        ).exists()
        
        if not has_access:
            logger.error(f"User {user_id} does not have access to thread {thread_id}")
            return []
        
        # Use the same queryset pattern as MessageViewSet
        messages_query = models.Message.objects.filter(thread=thread).select_related(
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
    Get a specific message by its ID with enhanced permission checking.
    Enhanced to use existing viewset patterns and permission checks.
    
    Args:
        message_id: UUID of the message
        user_id: UUID of the user (for permission checking)
        
    Returns:
        Message object or None if not found or no access
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Use the same pattern as MessageViewSet.get_queryset()
        message = models.Message.objects.filter(
            id=message_id,
            # Ensure user has access to the thread containing this message
            **{
                "id__in": models.Message.objects.filter(
                    Exists(
                        models.ThreadAccess.objects.filter(
                            mailbox__accesses__user=user, 
                            thread=OuterRef("thread_id")
                        )
                    )
                ).values_list('id', flat=True)
            }
        ).select_related('sender', 'thread').prefetch_related(
            'recipients__contact',
            'attachments__blob'
        ).first()
        
        if message:
            logger.info(f"Retrieved message: {message}")
            return message
        else:
            logger.error(f"Message {message_id} not found or user {user_id} has no access")
            return None
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
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
    include_archived: bool = False,
    use_elasticsearch: bool = True
) -> List[Dict[str, Any]]:
    """
    Search for messages based on various criteria.
    Enhanced to use existing search patterns and Elasticsearch integration.
    
    Args:
        user_id: UUID of the user performing the search
        query: Search query (subject, content, sender)
        mailbox_id: Optional specific mailbox to search in
        limit: Maximum number of results
        include_archived: Whether to include archived messages
        use_elasticsearch: Whether to use Elasticsearch for search (fallback to DB)
        
    Returns:
        List of dictionaries with message information
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Get user's accessible mailboxes using the same pattern as MailboxViewSet
        accesses = user.mailbox_accesses.all()
        user_mailboxes = models.Mailbox.objects.filter(
            id__in=accesses.values_list("mailbox_id", flat=True)
        )
        
        # If specific mailbox requested, validate access
        if mailbox_id:
            if not user_mailboxes.filter(id=mailbox_id).exists():
                logger.error(f"User {user_id} does not have access to mailbox {mailbox_id}")
                return []
            user_mailboxes = user_mailboxes.filter(id=mailbox_id)
        
        # Try Elasticsearch search first if enabled and query provided
        if use_elasticsearch and query:
            try:
                mailbox_ids_list = list(user_mailboxes.values_list('id', flat=True))
                search_results = search_threads(
                    query=query,
                    mailbox_ids=[str(mid) for mid in mailbox_ids_list],
                    size=limit
                )
                
                if search_results.get('threads'):
                    # Convert thread results to message format
                    results = []
                    thread_ids = [thread['id'] for thread in search_results['threads']]
                    
                    # Get messages from these threads
                    messages = models.Message.objects.filter(
                        thread_id__in=thread_ids,
                        is_draft=False,
                        is_trashed=False
                    ).select_related('sender', 'thread').order_by('-created_at')[:limit]
                    
                    if not include_archived:
                        messages = messages.filter(is_archived=False)
                    
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
                    
                    logger.info(f"Found {len(results)} messages via Elasticsearch for query: {query}")
                    return results
            except Exception as es_error:
                logger.warning(f"Elasticsearch search failed, falling back to database: {es_error}")
        
        # Fallback to database search using the same pattern as MessageViewSet
        messages_query = models.Message.objects.filter(
            Exists(
                models.ThreadAccess.objects.filter(
                    mailbox__in=user_mailboxes, 
                    thread=OuterRef("thread_id")
                )
            )
        ).select_related('sender', 'thread').prefetch_related('recipients__contact')
        
        # Apply search query if provided (database fallback)
        if query:
            messages_query = messages_query.filter(
                Q(subject__icontains=query) |
                Q(sender__name__icontains=query) |
                Q(sender__email__icontains=query)
            )
        
        # Apply filters
        if not include_archived:
            messages_query = messages_query.filter(is_archived=False)
        
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
    Enhanced to use existing viewset patterns and permission checks.
    
    Args:
        user_id: UUID of the user
        limit: Maximum number of messages to return
        
    Returns:
        List of dictionaries with unread message information
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Get user's accessible mailboxes using the same pattern as MailboxViewSet
        accesses = user.mailbox_accesses.all()
        user_mailboxes = models.Mailbox.objects.filter(
            id__in=accesses.values_list("mailbox_id", flat=True)
        )
        
        # Use the same pattern as MessageViewSet for permission checking
        messages = models.Message.objects.filter(
            Exists(
                models.ThreadAccess.objects.filter(
                    mailbox__in=user_mailboxes, 
                    thread=OuterRef("thread_id")
                )
            ),
            is_unread=True,
            is_draft=False,
            is_trashed=False
        ).select_related('sender', 'thread').order_by('-created_at')[:limit]
        
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
    Enhanced to use existing viewset patterns and permission checks.
    
    Args:
        user_id: UUID of the user
        days: Number of days to look back
        limit: Maximum number of messages to return
        
    Returns:
        List of dictionaries with recent message information
    """
    try:
        user = User.objects.get(id=user_id)
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Get user's accessible mailboxes using the same pattern as MailboxViewSet
        accesses = user.mailbox_accesses.all()
        user_mailboxes = models.Mailbox.objects.filter(
            id__in=accesses.values_list("mailbox_id", flat=True)
        )
        
        # Use the same pattern as MessageViewSet for permission checking
        messages = models.Message.objects.filter(
            Exists(
                models.ThreadAccess.objects.filter(
                    mailbox__in=user_mailboxes, 
                    thread=OuterRef("thread_id")
                )
            ),
            created_at__gte=cutoff_date,
            is_draft=False,
            is_trashed=False
        ).select_related('sender', 'thread').order_by('-created_at')[:limit]
        
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


def get_message_full_content(message_id: str, user_id: str) -> str:
    """
    Get the full text content of a message for chatbot processing.
    Enhanced to use existing viewset patterns and permission checks.
    
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


def retrieve_email_content_by_query(
    user_id: str,
    query: str,
    limit: int = 5,
    use_elasticsearch: bool = True
) -> Dict[str, Any]:
    """
    Retrieve the full content of the email that best matches a user query.
    Enhanced to use existing search patterns and Elasticsearch integration.
    
    Args:
        user_id: UUID of the user
        query: User query to find the most relevant email
        limit: Number of emails to search through to find the best match
        use_elasticsearch: Whether to use Elasticsearch for search
        
    Returns:
        Dictionary with the best matching email's full content and metadata
    """
    try:
        # First, search for emails matching the query using enhanced search
        search_results = search_messages(
            user_id=user_id, 
            query=query, 
            limit=limit,
            use_elasticsearch=use_elasticsearch
        )
        
        if not search_results:
            logger.info(f"No emails found for query: {query}")
            return {
                'success': False,
                'error': f'Aucun email trouvé pour la requête: {query}',
                'query': query
            }
        
        # Take the first (most relevant) result
        best_match = search_results[0]
        message_id = best_match['message_id']
        
        # Get the full content of the best matching email with permission check
        full_content = get_message_full_content(message_id, user_id)
        
        if not full_content:
            logger.error(f"Could not retrieve content for message {message_id}")
            return {
                'success': False,
                'error': f'Impossible de récupérer le contenu de l\'email trouvé',
                'query': query
            }
        
        # Get additional message details with permission check
        message = get_message_by_id(message_id, user_id)
        if message:
            parsed_content = get_parsed_message_content(message)
            
            logger.info(f"Successfully retrieved email content for query: {query}")
            return {
                'success': True,
                'email_content': full_content,
                'metadata': {
                    'message_id': message_id,
                    'thread_id': str(message.thread.id),
                    'subject': parsed_content['subject'],
                    'sender_name': parsed_content['sender']['name'],
                    'sender_email': parsed_content['sender']['email'],
                    'sent_at': parsed_content['sent_at'],
                    'is_unread': parsed_content['is_unread'],
                    'is_starred': parsed_content['is_starred'],
                },
                'query': query,
                'search_results_count': len(search_results),
                'search_method': 'elasticsearch' if use_elasticsearch else 'database'
            }
        else:
            return {
                'success': True,
                'email_content': full_content,
                'metadata': best_match,
                'query': query,
                'search_results_count': len(search_results),
                'search_method': 'elasticsearch' if use_elasticsearch else 'database'
            }
            
    except Exception as e:
        logger.error(f"Error retrieving email content for query '{query}': {e}")
        return {
            'success': False,
            'error': str(e),
            'query': query
        }


def get_thread_statistics(user_id: str, mailbox_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get thread statistics for a user, similar to the ThreadViewSet stats endpoint.
    
    Args:
        user_id: UUID of the user
        mailbox_id: Optional specific mailbox to get stats for
        
    Returns:
        Dictionary with thread statistics
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Get user's accessible mailboxes
        accesses = user.mailbox_accesses.all()
        user_mailboxes = models.Mailbox.objects.filter(
            id__in=accesses.values_list("mailbox_id", flat=True)
        )
        
        if mailbox_id:
            if not user_mailboxes.filter(id=mailbox_id).exists():
                logger.error(f"User {user_id} does not have access to mailbox {mailbox_id}")
                return {}
            user_mailboxes = user_mailboxes.filter(id=mailbox_id)
        
        # Base queryset: Threads the user has access to
        threads_queryset = models.Thread.objects.filter(
            Exists(
                models.ThreadAccess.objects.filter(
                    mailbox__in=user_mailboxes, 
                    thread=OuterRef("pk")
                )
            )
        ).distinct()
        
        # Calculate statistics similar to ThreadViewSet
        stats = {
            'total_threads': threads_queryset.count(),
            'unread_threads': threads_queryset.filter(has_unread=True).count(),
            'starred_threads': threads_queryset.filter(has_starred=True).count(),
            'draft_threads': threads_queryset.filter(has_draft=True).count(),
            'trashed_threads': threads_queryset.filter(has_trashed=True).count(),
            'spam_threads': threads_queryset.filter(is_spam=True).count(),
        }
        
        logger.info(f"Retrieved thread statistics for user {user_id}: {stats}")
        return stats
        
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
        return {}
    except Exception as e:
        logger.error(f"Error retrieving thread statistics: {e}")
        return {}


def search_threads_for_chatbot(
    user_id: str,
    query: str = "",
    mailbox_id: Optional[str] = None,
    limit: int = 10,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Search for threads using the existing search functionality.
    Enhanced wrapper around the core search functionality for chatbot use.
    
    Args:
        user_id: UUID of the user performing the search
        query: Search query 
        mailbox_id: Optional specific mailbox to search in
        limit: Maximum number of results
        filters: Optional filters (has_unread, has_starred, etc.)
        
    Returns:
        List of dictionaries with thread information
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Get user's accessible mailboxes
        accesses = user.mailbox_accesses.all()
        user_mailboxes = models.Mailbox.objects.filter(
            id__in=accesses.values_list("mailbox_id", flat=True)
        )
        
        if mailbox_id:
            if not user_mailboxes.filter(id=mailbox_id).exists():
                logger.error(f"User {user_id} does not have access to mailbox {mailbox_id}")
                return []
            user_mailboxes = user_mailboxes.filter(id=mailbox_id)
        
        # Try Elasticsearch search first if query provided
        if query:
            try:
                mailbox_ids_list = list(user_mailboxes.values_list('id', flat=True))
                search_results = search_threads(
                    query=query,
                    mailbox_ids=[str(mid) for mid in mailbox_ids_list],
                    size=limit
                )
                
                if search_results.get('threads'):
                    results = []
                    for thread_data in search_results['threads']:
                        # Get the actual thread object for additional data
                        try:
                            thread = models.Thread.objects.get(id=thread_data['id'])
                            results.append({
                                'thread_id': str(thread.id),
                                'subject': thread.subject,
                                'messaged_at': thread.messaged_at,
                                'has_unread': thread.has_unread,
                                'has_starred': thread.has_starred,
                                'has_draft': thread.has_draft,
                                'message_count': thread.messages.count(),
                                'participants': [
                                    msg.sender.email for msg in thread.messages.all()[:5]
                                ]
                            })
                        except models.Thread.DoesNotExist:
                            continue
                    
                    logger.info(f"Found {len(results)} threads via Elasticsearch for query: {query}")
                    return results
            except Exception as es_error:
                logger.warning(f"Elasticsearch search failed, falling back to database: {es_error}")
        
        # Fallback to database search
        threads_queryset = models.Thread.objects.filter(
            Exists(
                models.ThreadAccess.objects.filter(
                    mailbox__in=user_mailboxes, 
                    thread=OuterRef("pk")
                )
            )
        ).distinct()
        
        # Apply query filter if provided
        if query:
            threads_queryset = threads_queryset.filter(
                Q(subject__icontains=query) |
                Q(messages__sender__name__icontains=query) |
                Q(messages__sender__email__icontains=query)
            )
        
        # Apply additional filters
        if filters:
            for key, value in filters.items():
                if key in ['has_unread', 'has_starred', 'has_draft', 'has_trashed', 'is_spam']:
                    if value is True:
                        threads_queryset = threads_queryset.filter(**{key: True})
                    elif value is False:
                        threads_queryset = threads_queryset.filter(**{key: False})
        
        threads = threads_queryset.prefetch_related('messages__sender').order_by(
            '-messaged_at', '-created_at'
        )[:limit]
        
        results = []
        for thread in threads:
            results.append({
                'thread_id': str(thread.id),
                'subject': thread.subject,
                'messaged_at': thread.messaged_at,
                'has_unread': thread.has_unread,
                'has_starred': thread.has_starred,
                'has_draft': thread.has_draft,
                'message_count': thread.messages.count(),
                'participants': list(set([
                    msg.sender.email for msg in thread.messages.all()[:5]
                ]))
            })
        
        logger.info(f"Found {len(results)} threads for query: {query}")
        return results
        
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
        return []
    except Exception as e:
        logger.error(f"Error searching threads: {e}")
        return []
