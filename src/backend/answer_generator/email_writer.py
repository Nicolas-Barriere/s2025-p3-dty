"""
Email writing operations for response generation.

This module provides functionality to create draft email responses.
"""
import json
import logging
from typing import Dict, List, Optional, Any
from django.db import transaction
from django.utils import timezone

from core.models import (
    User, Mailbox, MailboxAccess, Thread, ThreadAccess, Message, Contact, 
    MessageRecipient
)
from core.enums import MessageRecipientTypeChoices, MailboxRoleChoices, ThreadAccessRoleChoices

logger = logging.getLogger(__name__)


class EmailWriterError(Exception):
    """Base exception for email writing operations."""
    pass


def get_or_create_contact(email: str, name: str, mailbox: Mailbox) -> Contact:
    """
    Get or create a contact for the given email address.
    """
    try:
        contact, created = Contact.objects.get_or_create(
            email=email,
            defaults={'name': name or '', 'last_seen_at': timezone.now()}
        )
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
    """
    logger.info(f"Starting create_draft_email: user_id={user_id}, mailbox_id={mailbox_id}, subject='{subject}'")
    
    try:
        with transaction.atomic():
            # Validate user and mailbox access
            user = User.objects.get(id=user_id)
            mailbox = Mailbox.objects.get(id=mailbox_id)
            
            # Check permissions
            try:
                access = MailboxAccess.objects.get(user=user, mailbox=mailbox)
                if access.role not in [MailboxRoleChoices.EDITOR, MailboxRoleChoices.ADMIN]:
                    logger.error(f"User {user_id} does not have EDITOR/ADMIN role for mailbox {mailbox_id}")
                    raise EmailWriterError("User cannot send emails from this mailbox")
            except MailboxAccess.DoesNotExist:
                logger.error(f"User {user_id} does not have access to mailbox {mailbox_id}")
                raise EmailWriterError("User does not have access to this mailbox")
            
            # Create sender contact
            sender_email = f"{mailbox.local_part}@{mailbox.domain.name}"
            sender_contact = get_or_create_contact(
                email=sender_email,
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
                    pass
            
            if thread_id and not thread:
                try:
                    thread = Thread.objects.get(id=thread_id)
                except Thread.DoesNotExist:
                    pass
            
            if not thread:
                # Create new thread
                thread = Thread.objects.create(
                    subject=subject,
                    snippet=body[:200] if body else '',
                    has_draft=True,
                    has_messages=False
                )
                
                # Create ThreadAccess to associate the thread with the mailbox
                thread_access, created = ThreadAccess.objects.get_or_create(
                    thread=thread,
                    mailbox=mailbox,
                    defaults={'role': ThreadAccessRoleChoices.EDITOR}
                )
                
            else:
                # Update thread to indicate it has drafts
                thread.has_draft = True
                thread.save()
                
                # Ensure ThreadAccess exists for this mailbox
                thread_access, created = ThreadAccess.objects.get_or_create(
                    thread=thread,
                    mailbox=mailbox,
                    defaults={'role': ThreadAccessRoleChoices.EDITOR}  
                )
            
            # Create the draft message
            draft_body_json = json.dumps({
                'content': body,
                'format': 'text'
            })
            
            message = Message.objects.create(
                thread=thread,
                subject=subject,
                sender=sender_contact,
                parent=parent_message,
                is_draft=True,
                is_sender=True,
                draft_body=draft_body_json
            )
            
            logger.info(f"Created draft message with ID: {message.id} in thread: {thread.id}")
            
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
            for recipient_data in recipients_bcc or []:
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
            
            return {
                'success': True,
                'message_id': str(message.id),
                'thread_id': str(thread.id)
            }
    
    except Exception as e:
        logger.error(f"Error creating draft email: {e}")
        raise EmailWriterError(f"Error creating draft email: {str(e)}")
