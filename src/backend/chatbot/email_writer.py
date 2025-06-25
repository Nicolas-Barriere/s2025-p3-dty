"""
Email writing operations for the chatbot.

This module provides functionality to:
- Create and send emails
- Create draft emails
- Reply to existing emails
- Forward emails
- Manage email recipients and attachments

Author: ANCT
Date: 2025-06-24
"""
import json
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

from core.models import (
    User, Mailbox, MailboxAccess, Thread, Message, Contact, 
    MessageRecipient, Blob, Attachment
)
from core.enums import MessageRecipientTypeChoices, MailboxRoleChoices

logger = logging.getLogger(__name__)


class EmailWriterError(Exception):
    """Base exception for email writing operations."""
    pass


class InsufficientPermissionsError(EmailWriterError):
    """Raised when user doesn't have sufficient permissions."""
    pass


class MailboxNotFoundError(EmailWriterError):
    """Raised when mailbox is not found or not accessible."""
    pass


class ContactNotFoundError(EmailWriterError):
    """Raised when contact is not found."""
    pass


def get_user_mailboxes(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all mailboxes accessible by a user.
    
    Args:
        user_id: User ID string
        
    Returns:
        List of mailbox dictionaries with permissions
        
    Raises:
        EmailWriterError: If user not found
    """
    try:
        if not user_id:
            raise EmailWriterError("User ID is required")
        
        # For now, we'll use user_id as the actual user ID
        # In a real implementation, you might need to resolve this differently
        user = User.objects.get(id=user_id)
        
        mailboxes = []
        for access in user.mailbox_accesses.select_related('mailbox', 'mailbox__domain'):
            mailbox = access.mailbox
            mailboxes.append({
                'id': str(mailbox.id),
                'email_address': f"{mailbox.local_part}@{mailbox.domain.name}",
                'local_part': mailbox.local_part,
                'domain': mailbox.domain.name,
                'role': access.role,
                'can_send': access.role in [MailboxRoleChoices.EDITOR, MailboxRoleChoices.ADMIN]
            })
        
        return mailboxes
        
    except User.DoesNotExist:
        logger.error(f"User not found: {user_id}")
        raise EmailWriterError(f"User not found: {user_id}")
    except Exception as e:
        logger.error(f"Error getting user mailboxes: {e}")
        raise EmailWriterError(f"Error getting user mailboxes: {str(e)}")


def get_or_create_contact(email: str, name: str, mailbox: Mailbox) -> Contact:
    """
    Get or create a contact for the given email address.
    
    Args:
        email: Email address
        name: Contact name (optional)
        mailbox: Mailbox instance
        
    Returns:
        Contact instance
    """
    try:
        contact, created = Contact.objects.get_or_create(
            email=email,
            mailbox=mailbox,
            defaults={'name': name or ''}
        )
        
        # Update name if provided and different
        if name and contact.name != name:
            contact.name = name
            contact.save()
            
        return contact
        
    except Exception as e:
        logger.error(f"Error getting/creating contact {email}: {e}")
        raise EmailWriterError(f"Error getting/creating contact: {str(e)}")


def create_draft_email(
    user_id: str,
    mailbox_id: str,
    subject: str,
    body: str,
    recipients_to: List[Dict[str, str]] = None,
    recipients_cc: List[Dict[str, str]] = None,
    recipients_bcc: List[Dict[str, str]] = None,
    parent_message_id: str = None,
    thread_id: str = None
) -> Dict[str, Any]:
    """
    Create a draft email.
    
    Args:
        user_id: User ID creating the draft
        mailbox_id: Source mailbox ID
        subject: Email subject
        body: Email body content
        recipients_to: List of TO recipients [{'email': 'x@y.com', 'name': 'Name'}]
        recipients_cc: List of CC recipients
        recipients_bcc: List of BCC recipients
        parent_message_id: ID of message being replied to (optional)
        thread_id: Thread ID (optional, will be created if not provided)
        
    Returns:
        Dictionary with draft information
        
    Raises:
        EmailWriterError: If operation fails
    """
    try:
        with transaction.atomic():
            # Validate user and mailbox access
            user = User.objects.get(id=user_id)
            mailbox = Mailbox.objects.get(id=mailbox_id)
            
            # Check permissions
            try:
                access = MailboxAccess.objects.get(user=user, mailbox=mailbox)
                if access.role not in [MailboxRoleChoices.EDITOR, MailboxRoleChoices.ADMIN]:
                    raise InsufficientPermissionsError("User cannot send emails from this mailbox")
            except MailboxAccess.DoesNotExist:
                raise InsufficientPermissionsError("User does not have access to this mailbox")
            
            # Create sender contact
            sender_contact = get_or_create_contact(
                email=f"{mailbox.local_part}@{mailbox.domain.name}",
                name=user.full_name or '',
                mailbox=mailbox
            )
            
            # Handle thread
            thread = None
            parent_message = None
            
            if parent_message_id:
                try:
                    parent_message = Message.objects.get(id=parent_message_id)
                    thread = parent_message.thread
                except Message.DoesNotExist:
                    logger.warning(f"Parent message {parent_message_id} not found")
            
            if thread_id and not thread:
                try:
                    thread = Thread.objects.get(id=thread_id)
                except Thread.DoesNotExist:
                    logger.warning(f"Thread {thread_id} not found")
            
            if not thread:
                # Create new thread
                thread = Thread.objects.create(
                    subject=subject,
                    snippet=body[:200] if body else '',
                    has_draft=True,
                    has_messages=False
                )
            else:
                # Update thread to indicate it has drafts
                thread.has_draft = True
                thread.save()
            
            # Create the draft message
            message = Message.objects.create(
                thread=thread,
                subject=subject,
                sender=sender_contact,
                parent=parent_message,
                is_draft=True,
                is_sender=True,
                draft_body=json.dumps({
                    'content': body,
                    'format': 'text'  # Could be 'html' in the future
                })
            )
            
            # Add recipients
            recipients_to = recipients_to or []
            recipients_cc = recipients_cc or []
            recipients_bcc = recipients_bcc or []
            
            # Process TO recipients
            for recipient_data in recipients_to:
                contact = get_or_create_contact(
                    email=recipient_data['email'],
                    name=recipient_data.get('name', ''),
                    mailbox=mailbox
                )
                MessageRecipient.objects.create(
                    message=message,
                    contact=contact,
                    type=MessageRecipientTypeChoices.TO
                )
            
            # Process CC recipients
            for recipient_data in recipients_cc:
                contact = get_or_create_contact(
                    email=recipient_data['email'],
                    name=recipient_data.get('name', ''),
                    mailbox=mailbox
                )
                MessageRecipient.objects.create(
                    message=message,
                    contact=contact,
                    type=MessageRecipientTypeChoices.CC
                )
            
            # Process BCC recipients
            for recipient_data in recipients_bcc:
                contact = get_or_create_contact(
                    email=recipient_data['email'],
                    name=recipient_data.get('name', ''),
                    mailbox=mailbox
                )
                MessageRecipient.objects.create(
                    message=message,
                    contact=contact,
                    type=MessageRecipientTypeChoices.BCC
                )
            
            logger.info(f"Created draft email {message.id} in thread {thread.id}")
            
            return {
                'success': True,
                'message_id': str(message.id),
                'thread_id': str(thread.id),
                'subject': subject,
                'recipients_count': len(recipients_to) + len(recipients_cc) + len(recipients_bcc),
                'is_draft': True
            }
            
    except User.DoesNotExist:
        raise EmailWriterError(f"User not found: {user_id}")
    except Mailbox.DoesNotExist:
        raise MailboxNotFoundError(f"Mailbox not found: {mailbox_id}")
    except InsufficientPermissionsError:
        raise
    except Exception as e:
        logger.error(f"Error creating draft email: {e}")
        raise EmailWriterError(f"Error creating draft email: {str(e)}")


def send_email(
    user_id: str,
    mailbox_id: str,
    subject: str,
    body: str,
    recipients_to: List[Dict[str, str]],
    recipients_cc: List[Dict[str, str]] = None,
    recipients_bcc: List[Dict[str, str]] = None,
    parent_message_id: str = None,
    thread_id: str = None,
    draft_message_id: str = None
) -> Dict[str, Any]:
    """
    Send an email immediately.
    
    Args:
        user_id: User ID sending the email
        mailbox_id: Source mailbox ID
        subject: Email subject
        body: Email body content
        recipients_to: List of TO recipients [{'email': 'x@y.com', 'name': 'Name'}]
        recipients_cc: List of CC recipients (optional)
        recipients_bcc: List of BCC recipients (optional)
        parent_message_id: ID of message being replied to (optional)
        thread_id: Thread ID (optional)
        draft_message_id: ID of existing draft to send (optional)
        
    Returns:
        Dictionary with sent email information
        
    Raises:
        EmailWriterError: If operation fails
    """
    try:
        with transaction.atomic():
            # If sending from draft, get the draft first
            if draft_message_id:
                try:
                    draft_message = Message.objects.get(id=draft_message_id, is_draft=True)
                    
                    # Update draft to sent status
                    draft_message.is_draft = False
                    draft_message.sent_at = timezone.now()
                    draft_message.save()
                    
                    # Update thread statistics
                    thread = draft_message.thread
                    thread.has_draft = False
                    thread.has_messages = True
                    thread.has_sender = True
                    thread.messaged_at = draft_message.sent_at
                    thread.save()
                    
                    logger.info(f"Sent draft email {draft_message.id}")
                    
                    return {
                        'success': True,
                        'message_id': str(draft_message.id),
                        'thread_id': str(thread.id),
                        'subject': draft_message.subject,
                        'sent_at': draft_message.sent_at.isoformat(),
                        'is_draft': False
                    }
                    
                except Message.DoesNotExist:
                    raise EmailWriterError(f"Draft message not found: {draft_message_id}")
            
            # Create and send new email
            result = create_draft_email(
                user_id=user_id,
                mailbox_id=mailbox_id,
                subject=subject,
                body=body,
                recipients_to=recipients_to,
                recipients_cc=recipients_cc,
                recipients_bcc=recipients_bcc,
                parent_message_id=parent_message_id,
                thread_id=thread_id
            )
            
            # Get the created message and send it
            message = Message.objects.get(id=result['message_id'])
            message.is_draft = False
            message.sent_at = timezone.now()
            message.save()
            
            # Update thread statistics
            thread = message.thread
            thread.has_draft = False
            thread.has_messages = True
            thread.has_sender = True
            thread.messaged_at = message.sent_at
            thread.save()
            
            logger.info(f"Sent email {message.id}")
            
            result.update({
                'sent_at': message.sent_at.isoformat(),
                'is_draft': False
            })
            
            return result
            
    except EmailWriterError:
        raise
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise EmailWriterError(f"Error sending email: {str(e)}")


def reply_to_email(
    user_id: str,
    original_message_id: str,
    body: str,
    reply_all: bool = False,
    as_draft: bool = False
) -> Dict[str, Any]:
    """
    Reply to an existing email.
    
    Args:
        user_id: User ID replying
        original_message_id: ID of message being replied to
        body: Reply body content
        reply_all: Whether to reply to all recipients
        as_draft: Whether to save as draft or send immediately
        
    Returns:
        Dictionary with reply information
        
    Raises:
        EmailWriterError: If operation fails
    """
    try:
        # Get the original message
        original_message = Message.objects.select_related(
            'thread', 'sender'
        ).prefetch_related('recipients__contact').get(id=original_message_id)
        
        # Get user's accessible mailboxes
        user_mailboxes = get_user_mailboxes(user_id)
        if not user_mailboxes:
            raise InsufficientPermissionsError("User has no accessible mailboxes")
        
        # Use the first available mailbox that can send emails
        sender_mailbox = None
        for mb in user_mailboxes:
            if mb['can_send']:
                sender_mailbox = mb
                break
        
        if not sender_mailbox:
            raise InsufficientPermissionsError("User has no mailboxes with send permissions")
        
        # Prepare recipients
        recipients_to = [{'email': original_message.sender.email, 'name': original_message.sender.name or ''}]
        recipients_cc = []
        
        if reply_all:
            # Add all original recipients except the sender mailbox
            for recipient in original_message.recipients.all():
                if recipient.contact.email != sender_mailbox['email_address']:
                    if recipient.type == MessageRecipientTypeChoices.TO:
                        recipients_to.append({
                            'email': recipient.contact.email, 
                            'name': recipient.contact.name or ''
                        })
                    elif recipient.type == MessageRecipientTypeChoices.CC:
                        recipients_cc.append({
                            'email': recipient.contact.email, 
                            'name': recipient.contact.name or ''
                        })
        
        # Prepare subject
        subject = original_message.subject
        if not subject.lower().startswith('re:'):
            subject = f"Re: {subject}"
        
        # Send or create draft
        if as_draft:
            return create_draft_email(
                user_id=user_id,
                mailbox_id=sender_mailbox['id'],
                subject=subject,
                body=body,
                recipients_to=recipients_to,
                recipients_cc=recipients_cc,
                parent_message_id=original_message_id,
                thread_id=str(original_message.thread.id)
            )
        else:
            return send_email(
                user_id=user_id,
                mailbox_id=sender_mailbox['id'],
                subject=subject,
                body=body,
                recipients_to=recipients_to,
                recipients_cc=recipients_cc,
                parent_message_id=original_message_id,
                thread_id=str(original_message.thread.id)
            )
            
    except Message.DoesNotExist:
        raise EmailWriterError(f"Original message not found: {original_message_id}")
    except EmailWriterError:
        raise
    except Exception as e:
        logger.error(f"Error replying to email: {e}")
        raise EmailWriterError(f"Error replying to email: {str(e)}")


def forward_email(
    user_id: str,
    original_message_id: str,
    recipients_to: List[Dict[str, str]],
    body: str = "",
    recipients_cc: List[Dict[str, str]] = None,
    as_draft: bool = False
) -> Dict[str, Any]:
    """
    Forward an existing email.
    
    Args:
        user_id: User ID forwarding
        original_message_id: ID of message being forwarded
        recipients_to: List of recipients to forward to
        body: Additional message body (optional)
        recipients_cc: CC recipients (optional)
        as_draft: Whether to save as draft or send immediately
        
    Returns:
        Dictionary with forward information
        
    Raises:
        EmailWriterError: If operation fails
    """
    try:
        # Get the original message
        original_message = Message.objects.select_related('sender').get(id=original_message_id)
        
        # Get user's accessible mailboxes
        user_mailboxes = get_user_mailboxes(user_id)
        if not user_mailboxes:
            raise InsufficientPermissionsError("User has no accessible mailboxes")
        
        # Use the first available mailbox that can send emails
        sender_mailbox = None
        for mb in user_mailboxes:
            if mb['can_send']:
                sender_mailbox = mb
                break
        
        if not sender_mailbox:
            raise InsufficientPermissionsError("User has no mailboxes with send permissions")
        
        # Prepare subject
        subject = original_message.subject
        if not subject.lower().startswith('fwd:') and not subject.lower().startswith('fw:'):
            subject = f"Fwd: {subject}"
        
        # Prepare body with original message info
        original_body = ""
        if original_message.draft_body:
            try:
                draft_data = json.loads(original_message.draft_body)
                original_body = draft_data.get('content', '')
            except json.JSONDecodeError:
                original_body = original_message.draft_body
        
        full_body = f"{body}\n\n---------- Forwarded message ----------\n"
        full_body += f"From: {original_message.sender}\n"
        full_body += f"Subject: {original_message.subject}\n"
        full_body += f"Date: {original_message.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        full_body += original_body
        
        # Send or create draft
        if as_draft:
            return create_draft_email(
                user_id=user_id,
                mailbox_id=sender_mailbox['id'],
                subject=subject,
                body=full_body,
                recipients_to=recipients_to,
                recipients_cc=recipients_cc
            )
        else:
            return send_email(
                user_id=user_id,
                mailbox_id=sender_mailbox['id'],
                subject=subject,
                body=full_body,
                recipients_to=recipients_to,
                recipients_cc=recipients_cc
            )
            
    except Message.DoesNotExist:
        raise EmailWriterError(f"Original message not found: {original_message_id}")
    except EmailWriterError:
        raise
    except Exception as e:
        logger.error(f"Error forwarding email: {e}")
        raise EmailWriterError(f"Error forwarding email: {str(e)}")


def delete_draft(user_id: str, draft_message_id: str) -> Dict[str, Any]:
    """
    Delete a draft email.
    
    Args:
        user_id: User ID deleting the draft
        draft_message_id: ID of draft message to delete
        
    Returns:
        Dictionary with deletion status
        
    Raises:
        EmailWriterError: If operation fails
    """
    try:
        with transaction.atomic():
            # Get the draft message
            draft_message = Message.objects.select_related('thread').get(
                id=draft_message_id, 
                is_draft=True
            )
            
            # Verify user has permission to delete this draft
            # This is a simplified check - in practice you'd want more sophisticated permission checking
            user = User.objects.get(id=user_id)
            sender_mailbox_email = draft_message.sender.email
            
            # Check if user has access to the sender mailbox
            user_mailboxes = get_user_mailboxes(user_id)
            has_permission = any(mb['email_address'] == sender_mailbox_email for mb in user_mailboxes)
            
            if not has_permission:
                raise InsufficientPermissionsError("User cannot delete this draft")
            
            thread = draft_message.thread
            
            # Delete the draft
            draft_message.delete()
            
            # Update thread statistics
            thread.has_draft = thread.messages.filter(is_draft=True).exists()
            thread.save()
            
            logger.info(f"Deleted draft email {draft_message_id}")
            
            return {
                'success': True,
                'message': 'Draft deleted successfully'
            }
            
    except Message.DoesNotExist:
        raise EmailWriterError(f"Draft message not found: {draft_message_id}")
    except User.DoesNotExist:
        raise EmailWriterError(f"User not found: {user_id}")
    except EmailWriterError:
        raise
    except Exception as e:
        logger.error(f"Error deleting draft: {e}")
        raise EmailWriterError(f"Error deleting draft: {str(e)}")
