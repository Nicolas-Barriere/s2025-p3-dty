"""
Simplified Email Service for Chatbot Integration.

This module provides a clean, class-based interface for email retrieval and search
for the chatbot. Only includes essential functions needed for the simplified architecture:
- Get 500 most recent emails with full metadata
- Send all emails to Albert API for intelligent search
- Format results for mailbox display

Removed functions:
- All fallback/manual search logic
- Thread statistics and unread message functions
- Individual message retrieval functions
- Test and summary functions
"""

import json
import re
import html
import time
import logging
from typing import Dict, List, Optional, Any, Set
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils import timezone


from core import models
from .rag import RAGSystem

logger = logging.getLogger(__name__)
User = get_user_model()

# RAG system instance to be used for embedding and retrieval
rag_system = RAGSystem()


class EmailService:
    """
    Simplified email service for chatbot integration.
    
    Provides a clean interface for:
    1. Getting user's accessible mailboxes
    2. Retrieving 500 most recent emails with full metadata
    3. Intelligent email search using Albert API
    4. Formatting results for mailbox display
    """
    
    def __init__(self):
        """Initialize the email service."""
        self.logger = logger
    
    def get_user_accessible_mailboxes(self, user_id: str) -> List[models.Mailbox]:
        """
        Get all mailboxes that a user has access to.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            List of Mailbox objects the user can access
        """
        try:
            self.logger.info(f"Getting accessible mailboxes for user_id: {user_id}")
            
            user = User.objects.get(id=user_id)
            self.logger.debug(f"Found user: {user.email if hasattr(user, 'email') else user}")
            
            # Use the user's mailbox_accesses relationship to get accessible mailboxes
            mailboxes = models.Mailbox.objects.filter(
                accesses__user=user
            ).select_related('domain', 'contact').order_by("-created_at")
            
            mailbox_count = mailboxes.count()
            self.logger.info(f"Found {mailbox_count} accessible mailboxes for user {user}")
            
            if mailbox_count > 0:
                mailbox_list = list(mailboxes)
                self.logger.debug(f"Mailbox IDs: {[str(mb.id) for mb in mailbox_list[:5]]}")  # Log first 5 IDs
                return mailbox_list
            else:
                self.logger.warning(f"No accessible mailboxes found for user {user}")
                return []
                
        except User.DoesNotExist:
            self.logger.error(f"User with ID {user_id} not found")
            return []
        except Exception as e:
            self.logger.error(f"Error retrieving mailboxes for user {user_id}: {e}", exc_info=True)
            return []
    
    def get_recent_messages(self, mailboxes: List[models.Mailbox], limit: int = 500) -> List[models.Message]:
        """
        Get the most recent messages from the given mailboxes.
        
        Args:
            mailboxes: List of Mailbox objects
            limit: Maximum number of messages to retrieve (default: 500)
            
        Returns:
            List of Message objects
        """
        try:
            self.logger.info(f"Getting recent messages from {len(mailboxes)} mailboxes, limit: {limit}")
            
            if not mailboxes:
                self.logger.warning("No mailboxes provided to get_recent_messages")
                return []
            
            mailbox_ids = [mb.id for mb in mailboxes]
            self.logger.debug(f"Searching messages in mailbox IDs: {mailbox_ids[:5]}")  # Log first 5 IDs
            
            # Messages are related to threads, and threads have access to mailboxes
            # So we need to query through: Message -> Thread -> ThreadAccess -> Mailbox
            messages = models.Message.objects.filter(
                thread__accesses__mailbox__id__in=mailbox_ids,
                is_draft=False,
                is_trashed=False
            ).select_related(
                'sender', 'thread'
            ).order_by('-created_at')[:limit]
            
            message_list = list(messages)
            message_count = len(message_list)
            
            self.logger.info(f"Retrieved {message_count} messages from {len(mailboxes)} mailboxes")
            
            if message_count > 0:
                # Log some message details for debugging
                first_msg = message_list[0]
                last_msg = message_list[-1]
                self.logger.debug(f"Date range: {last_msg.created_at} to {first_msg.created_at}")
                self.logger.debug(f"Sample message IDs: {[str(msg.id) for msg in message_list[:3]]}")
            else:
                self.logger.warning("No messages found in the provided mailboxes")
            
            return message_list
            
        except Exception as e:
            self.logger.error(f"Error retrieving recent messages: {e}", exc_info=True)
            return []
    
    def get_parsed_message_content(self, message: models.Message) -> str:
        """
        Get parsed text content from a message for chatbot processing.
        
        Args:
            message: Message object
            
        Returns:
            String containing the parsed text content
        """
        try:
            self.logger.debug(f"Parsing message {message.id} - {message.subject}")
            
            # Use the message's built-in get_parsed_data method
            parsed_data = message.get_parsed_data()
            self.logger.debug(f"Parsed data keys: {list(parsed_data.keys())}")
            
            # Extract text content
            text_content = ""
            text_body = parsed_data.get('textBody', [])
            html_body = parsed_data.get('htmlBody', [])
            self.logger.debug(f"Text body parts: {len(text_body)}, HTML body parts: {len(html_body)}")
            
            # Try to get text body first
            if text_body:
                for text_part in text_body:
                    if isinstance(text_part, dict) and 'content' in text_part:
                        text_content += text_part['content'] + "\n"
                    elif isinstance(text_part, str):
                        text_content += text_part + "\n"
            
            # If no text body, try HTML body (basic extraction)
            if not text_content and html_body:
                self.logger.debug(f"No text body, extracting from HTML")
                for html_part in html_body:
                    if isinstance(html_part, dict) and 'content' in html_part:
                        # Basic HTML to text conversion
                        html_content = html_part['content']
                        # Remove HTML tags
                        clean_text = re.sub(r'<[^>]+>', '', html_content)
                        # Decode HTML entities
                        clean_text = html.unescape(clean_text)
                        text_content += clean_text + "\n"
            
            # Clean up the text content
            text_content = text_content.strip()
            
            self.logger.debug(f"Extracted {len(text_content)} characters of text content")
            return text_content
            
        except Exception as e:
            self.logger.error(f"Error parsing message content for {message}: {e}", exc_info=True)
            return ""
    
    def get_parsed_message_details(self, message: models.Message) -> Dict[str, Any]:
        """
        Get parsed content details from a message using the model's built-in parsing methods.
        
        Args:
            message: Message object
            
        Returns:
            Dictionary with parsed message content and metadata
        """
        try:
            self.logger.debug(f"Parsing message details {message.id} - {message.subject}")
            
            # Use the message's built-in get_parsed_data method
            parsed_data = message.get_parsed_data()
            self.logger.debug(f"Parsed data keys: {list(parsed_data.keys())}")
            
            # Extract text and HTML content
            text_body = parsed_data.get('textBody', [])
            html_body = parsed_data.get('htmlBody', [])
            self.logger.debug(f"Text body parts: {len(text_body)}, HTML body parts: {len(html_body)}")
            
            # Get attachments using the message's attachments relationship
            attachments = []
            for attachment in message.attachments.all():
                attachments.append({
                    'name': attachment.name,
                    'size': attachment.size,
                    'content_type': attachment.content_type,
                })
            self.logger.debug(f"Found {len(attachments)} attachments")
            
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
            self.logger.debug(f"Recipients - To: {len(recipients['to'])}, CC: {len(recipients['cc'])}, BCC: {len(recipients['bcc'])}")
            
            result = {
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
            
            self.logger.debug(f"Successfully parsed message {message.id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing message content for {message}: {e}", exc_info=True)
            return {
                'subject': message.subject,
                'error': str(e)
            }
    
    def get_email_context_for_chatbot(self, user_id: str) -> Dict[str, Any]:
        """
        Main function to gather email context for the chatbot.
        Gets the 500 most recent emails with all available information.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Dictionary containing email context and metadata
        """
        start_time = time.time()
        self.logger.info(f"Getting email context for chatbot - user_id: {user_id}")
        
        try:
            # Step 1: Get accessible mailboxes
            self.logger.info("Step 1: Getting accessible mailboxes")
            mailboxes = self.get_user_accessible_mailboxes(user_id)
            
            if not mailboxes:
                self.logger.warning(f"No accessible mailboxes found for user {user_id}")
                return {
                    "success": False,
                    "error": "No accessible mailboxes found",
                    "emails": [],
                    "total_emails": 0,
                    "mailbox_count": 0,
                    "processing_time": time.time() - start_time
                }
            
            self.logger.info(f"Step 1 completed: Found {len(mailboxes)} accessible mailboxes")
            
            # Step 2: Get recent messages with full details
            self.logger.info("Step 2: Getting recent messages with full details")
            recent_message_objects = self.get_recent_messages(mailboxes, limit=500)
            
            if not recent_message_objects:
                self.logger.warning(f"No messages found in mailboxes for user {user_id}")
                return {
                    "success": False,
                    "error": "No messages found",
                    "emails": [],
                    "total_emails": 0,
                    "mailbox_count": len(mailboxes),
                    "processing_time": time.time() - start_time
                }
            
            self.logger.info(f"Step 2 completed: Retrieved {len(recent_message_objects)} messages")
            
            # Step 3: Extract complete email information
            self.logger.info("Step 3: Extracting complete email information")
            emails_with_full_info = []
            
            for i, message in enumerate(recent_message_objects):
                if i < 10:  # Log details for first 10 messages
                    self.logger.debug(f"Processing message {i+1}: ID={message.id}, subject={message.subject[:50]}...")
                
                # Get full parsed content and details
                parsed_details = self.get_parsed_message_details(message)
                text_content = self.get_parsed_message_content(message)
                
                # Get attachment information
                attachments = []
                for attachment in message.attachments.all():
                    attachments.append({
                        'name': attachment.name,
                        'size': attachment.size,
                        'content_type': attachment.content_type,
                    })
                
                # Build complete email data
                email_data = {
                    "id": str(message.id),
                    "subject": message.subject,
                    "content": text_content,
                    "sender": {
                        "name": message.sender.name,
                        "email": message.sender.email
                    },
                    "recipients": parsed_details.get('recipients', {}),
                    "sent_at": message.sent_at.isoformat() if message.sent_at else None,
                    "created_at": message.created_at.isoformat(),
                    "thread_id": str(message.thread.id),
                    "thread_subject": message.thread.subject,
                    "attachments": attachments,
                    "attachment_count": len(attachments),
                    "flags": {
                        "is_unread": message.is_unread,
                        "is_starred": message.is_starred,
                        "is_draft": message.is_draft,
                        "is_trashed": message.is_trashed,
                        "is_spam": message.is_spam,
                        "is_archived": message.is_archived,
                        "is_sender": message.is_sender
                    }
                }
                
                emails_with_full_info.append(email_data)
            
            self.logger.info(f"Step 3 completed: Processed {len(emails_with_full_info)} emails with full information")
            
            processing_time = time.time() - start_time
            
            result = {
                "success": True,
                "emails": emails_with_full_info,
                "total_emails": len(emails_with_full_info),
                "mailbox_count": len(mailboxes),
                "processing_time": processing_time
            }
            
            self.logger.info(f"Email context retrieval completed successfully: "
                           f"{len(emails_with_full_info)} emails retrieved, "
                           f"processing time: {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Error in get_email_context_for_chatbot for user {user_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Error retrieving email context: {str(e)}",
                "emails": [],
                "total_emails": 0,
                "mailbox_count": 0,
                "processing_time": processing_time
            }
    
    def parse_ai_response_for_email_search(self, ai_content: str, context_emails: List[Dict]) -> List[Dict[str, Any]]:
        """
        Parse AI response for email search and return formatted results for mailbox display.
        
        Args:
            ai_content: Raw AI response content
            context_emails: List of email context objects
            
        Returns:
            List of formatted search results compatible with mailbox display
        """
        try:
            self.logger.info(f"Parsing AI response (length: {len(ai_content)} chars)")
            self.logger.info(f"AI response content: {ai_content}")  # Log full content
            
            # Create a lookup dictionary for emails by ID
            email_lookup = {email['id']: email for email in context_emails}
            self.logger.info(f"Created email lookup with {len(email_lookup)} emails")
            
            # Try to parse JSON response
            try:
                self.logger.info("Looking for JSON array in AI response...")
                # Look for JSON array in the response
                json_match = re.search(r'\[.*?\]', ai_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    self.logger.info(f"Found JSON string: {json_str}")
                    ai_results = json.loads(json_str)
                    self.logger.info(f"Successfully parsed JSON with {len(ai_results)} results")
                else:
                    self.logger.warning("No JSON array found in AI response")
                    self.logger.warning(f"AI response content: {ai_content}")
                    return []
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON from AI response: {e}")
                self.logger.warning(f"JSON string that failed: {json_str if 'json_str' in locals() else 'No JSON string'}")
                return []
            
            # Process AI results and format for mailbox display (like Elasticsearch results)
            formatted_results = []
            for result in ai_results:
                email_id = result.get('id', '')
                if email_id in email_lookup:
                    email = email_lookup[email_id]
                    
                    # Format result like Elasticsearch search results (compatible with mailbox display)
                    formatted_result = {
                        'message_id': email_id,
                        'thread_id': email.get('thread_id', ''),
                        'subject': email.get('subject', ''),
                        'from': email.get('sender', {}).get('email', ''),  # Frontend expects 'from'
                        'sender_name': email.get('sender', {}).get('name', ''),
                        'sender_email': email.get('sender', {}).get('email', ''),
                        'date': email.get('sent_at'),  # Frontend expects 'date'
                        'sent_at': email.get('sent_at'),
                        'snippet': email.get('content', '')[:200] if email.get('content') else '',  # Frontend expects 'snippet'
                        'is_unread': email.get('flags', {}).get('is_unread', False),
                        'is_starred': email.get('flags', {}).get('is_starred', False),
                        'thread_subject': email.get('thread_subject', ''),
                        'relevance_score': result.get('relevance_score', 0.5),
                        'ai_reason': result.get('reason', 'AI identified as relevant'),
                        # Additional metadata for debugging
                        'attachment_count': email.get('attachment_count', 0),
                        'content_preview': email.get('content', '')[:200] if email.get('content') else '',
                    }
                    formatted_results.append(formatted_result)
                    self.logger.debug(f"Added result for email {email_id} with score {result.get('relevance_score', 0.5)}")
                else:
                    self.logger.warning(f"AI returned email ID {email_id} not found in context")
            
            # Sort by relevance score (highest first)
            formatted_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            self.logger.info(f"Successfully parsed {len(formatted_results)} email search results from AI response")
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Error parsing AI response for email search: {e}", exc_info=True)
            return []
    
    def chatbot_intelligent_email_search(
        self, 
        user_id: str, 
        user_query: str, 
        api_client,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Perform intelligent email search using RAG system with embeddings.
        This method:
        1. Retrieves the most recent 500 emails
        2. Checks if emails are already indexed in the RAG system
        3. Indexes any new emails
        4. Uses the query to retrieve the most relevant emails
        
        Args:
            user_id: UUID of the user
            user_query: User's natural language search query
            api_client: Albert API client instance
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary containing search results and metadata
        """
        search_start_time = time.time()
        self.logger.info(f"Starting intelligent email search with RAG - user_id: {user_id}, query: '{user_query[:100]}...'")
        
        try:
            # Step 1: Get all email context
            self.logger.info("Step 1: Fetching email context")
            context_result = self.get_email_context_for_chatbot(user_id)
            
            if not context_result["success"]:
                self.logger.error(f"Failed to get email context: {context_result.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": f"Failed to retrieve emails: {context_result.get('error', 'Unknown error')}",
                    "results": [],
                    "search_method": "none",
                    "total_searched": 0,
                    "processing_time": time.time() - search_start_time
                }
            
            context_emails = context_result["emails"]
            self.logger.info(f"Step 1 completed: Retrieved {len(context_emails)} emails for search")
            
            if not context_emails:
                self.logger.warning("No emails available for search")
                return {
                    "success": True,
                    "results": [],
                    "message": "No emails found to search",
                    "search_method": "none",
                    "total_searched": 0,
                    "processing_time": time.time() - search_start_time
                }
            
            # Step 2: Set user-specific collection and check if it exists
            self.logger.info("Step 2: Setting user-specific RAG collection")
            rag_system.set_user_collection(user_id)
            
            if not rag_system.collection_id:
                self.logger.info("Step 2: Creating new RAG collection for user")
                rag_system.create_collection()
                self.logger.info(f"Step 2 completed: Created RAG collection: {rag_system.collection_id}")
            else:
                self.logger.info(f"Step 2: Using existing RAG collection: {rag_system.collection_id}")
                self.logger.info(f"Step 2: Found {len(rag_system.indexed_email_ids)} previously indexed emails")
            
            # Step 3: Prepare emails for indexing - format for RAG system
            self.logger.info("Step 3: Preparing emails for RAG indexing")
            emails_for_rag = []
            
            # Limit the number of emails to avoid overwhelming the Albert API
            max_emails_to_index = min(rag_system.config.max_emails_per_batch, len(context_emails))
            emails_to_process = context_emails[:max_emails_to_index]
            
            self.logger.info(f"Processing {len(emails_to_process)} emails out of {len(context_emails)} available")
            
            # Keep track of email IDs to ensure we're only processing unique emails
            for email in emails_to_process:
                email_id = email['id']
                
                # Create a complete email document for RAG indexing
                # We include the subject in the body to ensure it's part of the embedding
                full_content = f"Subject: {email.get('subject', '')}\n\n"
                full_content += f"From: {email.get('sender', {}).get('name', '')} <{email.get('sender', {}).get('email', '')}>\n"
                
                # Add recipients information
                recipients = email.get('recipients', {})
                if recipients.get('to'):
                    to_emails = [f"{r.get('name', '')} <{r.get('email', '')}>".strip() for r in recipients.get('to', [])]
                    full_content += f"To: {', '.join(to_emails)}\n"
                
                if recipients.get('cc'):
                    cc_emails = [f"{r.get('name', '')} <{r.get('email', '')}>".strip() for r in recipients.get('cc', [])]
                    full_content += f"CC: {', '.join(cc_emails)}\n"
                
                # Add date information
                full_content += f"Date: {email.get('sent_at', '')}\n\n"
                
                # Add the actual content
                full_content += email.get('content', '')
                
                # Add attachment information
                if email.get('attachment_count', 0) > 0:
                    attachment_names = [att.get('name', '') for att in email.get('attachments', [])]
                    full_content += f"\n\nAttachments: {', '.join(attachment_names)}"
                
                # Add to the RAG indexing list with metadata
                emails_for_rag.append({
                    'id': email_id,
                    'body': full_content,
                    'metadata': {
                        'subject': email.get('subject', ''),
                        'sender': email.get('sender', {}).get('email', ''),
                        'date': email.get('sent_at', ''),
                        'thread_id': email.get('thread_id', '')
                    }
                })
            
            self.logger.info(f"Step 3 completed: Prepared {len(emails_for_rag)} emails for RAG indexing")
            
            # Step 4: Index emails in RAG system (with smart reindexing)
            self.logger.info("Step 4: Checking if email indexing is needed")
            try:
                rag_system.index_emails(emails_for_rag)
                self.logger.info(f"Step 4 completed: Email indexing process finished")
            except Exception as index_error:
                self.logger.error(f"Failed to index emails in RAG system: {index_error}", exc_info=True)
                
                # Check if this is a complete failure or partial failure
                if "Failed to index any emails" in str(index_error):
                    # Complete failure - return error
                    return {
                        "success": False,
                        "error": f"Failed to index emails: {str(index_error)}",
                        "results": [],
                        "search_method": "rag_error",
                        "total_searched": len(context_emails),
                        "processing_time": time.time() - search_start_time
                    }
                else:
                    # Partial failure - log warning but continue
                    self.logger.warning(f"Some emails failed to index, but continuing with partial collection: {index_error}")
                    # Continue to query step
            
            # Step 5: Query the RAG system with the user's query
            self.logger.info(f"Step 5: Querying RAG system with user query: '{user_query}'")
            try:
                query_start_time = time.time()
                relevant_contents = rag_system.query_emails(user_query, k=max_results)
                query_time = time.time() - query_start_time
                
                self.logger.info(f"Step 5 completed: Retrieved {len(relevant_contents)} relevant emails in {query_time:.2f}s")
                
                # Log detailed scores for all retrieved emails
                if relevant_contents:
                    self.logger.info("=== RAG RETRIEVAL SCORES ===")
                    for i, result in enumerate(relevant_contents):
                        score = result.get("score", 0.0)
                        document_name = result.get("metadata", {}).get("document_name", "unknown")
                        content_preview = result.get("content", "")[:100].replace('\n', ' ')
                        self.logger.info(f"  #{i+1:2d}: Score {score:.4f} | {document_name} | Preview: {content_preview}...")
                    
                    scores = [result.get("score", 0.0) for result in relevant_contents]
                    avg_score = sum(scores) / len(scores)
                    min_score = min(scores)
                    max_score = max(scores)
                    self.logger.info(f"Score Statistics: Max={max_score:.4f}, Min={min_score:.4f}, Avg={avg_score:.4f}")
                    self.logger.info("=== END RAG SCORES ===")
                
                if not relevant_contents:
                    self.logger.warning("RAG query returned no results")
                    return {
                        "success": True,
                        "results": [],
                        "message": "No relevant emails found",
                        "search_method": "rag",
                        "total_searched": len(context_emails),
                        "processing_time": time.time() - search_start_time
                    }
                
                # Step 6: Match RAG results to original emails and format for frontend
                self.logger.info("Step 6: Matching RAG results to original emails")
                
                # Create email lookup by ID
                email_lookup = {email['id']: email for email in context_emails}
                
                # Calculate dynamic score threshold based on highest score
                if relevant_contents:
                    scores = [result.get("score", 0.0) for result in relevant_contents]
                    highest_score = max(scores) if scores else 0.0
                    dynamic_threshold = highest_score * rag_system.config.min_relevance_score_percentage
                    self.logger.info(f"Dynamic threshold: {dynamic_threshold:.3f} ({rag_system.config.min_relevance_score_percentage:.1%} of highest score {highest_score:.3f})")
                else:
                    dynamic_threshold = 0.0
                
                # Format results for frontend
                formatted_results = []
                
                for i, result in enumerate(relevant_contents):
                    content = result.get("content", "")
                    metadata = result.get("metadata", {})
                    document_name = metadata.get("document_name", "")
                    score = result.get("score", 0.0)
                    
                    matched_email_id = None
                    
                    # Method 1: Extract email ID from document filename
                    # The filename format is email_{i}_{email_id}.txt
                    if document_name:
                        self.logger.debug(f"Trying to match document: {document_name}")
                        # Extract email ID from filename like "email_5_12345abc-def0-1234-abcd-123456789abc.txt"
                        if document_name.startswith("email_") and document_name.endswith(".txt"):
                            # Remove the .txt extension and split by underscore
                            base_name = document_name.replace('.txt', '')
                            parts = base_name.split('_')
                            if len(parts) >= 3:
                                # The email ID should be everything after the second underscore
                                # In case the email ID itself contains underscores
                                potential_email_id = '_'.join(parts[2:])
                                if potential_email_id in email_lookup:
                                    matched_email_id = potential_email_id
                                    self.logger.debug(f"✅ Matched email via filename: {document_name} -> {matched_email_id}")
                                else:
                                    self.logger.debug(f"❌ Email ID '{potential_email_id}' from filename not found in lookup")
                            else:
                                self.logger.debug(f"❌ Filename format unexpected: {document_name}")
                        else:
                            self.logger.debug(f"❌ Filename doesn't match expected pattern: {document_name}")
                    
                    # Method 2: Search for email ID directly in the metadata  
                    if not matched_email_id and metadata:
                        # Check if there's an email ID in the metadata
                        if 'email_id' in metadata and metadata['email_id'] in email_lookup:
                            matched_email_id = metadata['email_id']
                            self.logger.debug(f"✅ Matched email via metadata: {matched_email_id}")
                    
                    # Method 3: Search for email ID in content
                    if not matched_email_id:
                        for email_id in email_lookup.keys():
                            if email_id in content:
                                matched_email_id = email_id
                                self.logger.debug(f"✅ Matched email via content search: {matched_email_id}")
                                break
                    
                    # Method 4: Fuzzy matching based on subject and sender
                    if not matched_email_id:
                        best_match_id = None
                        best_match_score = 0
                        
                        # Extract subject from content (it should be at the beginning)
                        content_lines = content.split('\n')
                        content_subject = ""
                        content_sender = ""
                        
                        for line in content_lines[:5]:  # Check first few lines
                            if line.startswith("Subject: "):
                                content_subject = line.replace("Subject: ", "").strip()
                            elif line.startswith("From: "):
                                content_sender = line.replace("From: ", "").strip()
                        
                        if content_subject or content_sender:
                            for email_id, email in email_lookup.items():
                                match_score = 0
                                
                                # Score based on subject similarity
                                if content_subject and email.get('subject'):
                                    subject_words_content = set(content_subject.lower().split())
                                    subject_words_email = set(email.get('subject', '').lower().split())
                                    subject_overlap = len(subject_words_content & subject_words_email)
                                    if subject_overlap > 0:
                                        match_score += subject_overlap * 10
                                
                                # Score based on sender similarity
                                if content_sender and email.get('sender', {}).get('email'):
                                    if email.get('sender', {}).get('email').lower() in content_sender.lower():
                                        match_score += 20
                                
                                if match_score > best_match_score:
                                    best_match_score = match_score
                                    best_match_id = email_id
                        
                        if best_match_score > 15:  # Threshold for a good match
                            matched_email_id = best_match_id
                            self.logger.debug(f"✅ Matched email via fuzzy matching: {matched_email_id} (score: {best_match_score})")
                    
                    if matched_email_id and matched_email_id in email_lookup:
                        email = email_lookup[matched_email_id]
                        
                        # Use the Albert API score if available, otherwise calculate based on position
                        relevance_score = score if score > 0 else (1.0 - (i / max(len(relevant_contents), 1)))
                        
                        # Apply dynamic score threshold filtering - only include results above percentage of highest score
                        if relevance_score < dynamic_threshold:
                            self.logger.info(f"🚫 FILTERED: Email {matched_email_id[:8]}... | Score: {relevance_score:.4f} < Threshold: {dynamic_threshold:.4f} | Subject: {email.get('subject', 'No subject')[:50]}...")
                            continue
                        
                        self.logger.info(f"✅ INCLUDED: Email {matched_email_id[:8]}... | Score: {relevance_score:.4f} ≥ Threshold: {dynamic_threshold:.4f} | Subject: {email.get('subject', 'No subject')[:50]}...")
                        
                        # Format result for frontend compatibility
                        formatted_result = {
                            'id': matched_email_id,  # Frontend expects 'id'
                            'message_id': matched_email_id,
                            'thread_id': email.get('thread_id', ''),
                            'subject': email.get('subject', ''),
                            'from': email.get('sender', {}).get('email', ''),  # Frontend expects 'from'
                            'sender': {  # Frontend expects 'sender' object
                                'email': email.get('sender', {}).get('email', ''),
                                'name': email.get('sender', {}).get('name', '')
                            },
                            'sender_name': email.get('sender', {}).get('name', ''),
                            'sender_email': email.get('sender', {}).get('email', ''),
                            'date': email.get('sent_at'),  # Frontend expects 'date'
                            'sent_at': email.get('sent_at'),
                            'snippet': email.get('content', '')[:200] if email.get('content') else '',  # Frontend expects 'snippet'
                            'is_unread': email.get('flags', {}).get('is_unread', False),
                            'is_starred': email.get('flags', {}).get('is_starred', False),
                            'thread_subject': email.get('thread_subject', ''),
                            'relevance_score': relevance_score,
                            'ai_reason': f"Semantically relevant to query: '{user_query}' (score: {relevance_score:.3f}, threshold: {dynamic_threshold:.3f})",
                            # Additional metadata for debugging
                            'attachment_count': email.get('attachment_count', 0),
                            'content_preview': email.get('content', '')[:200] if email.get('content') else '',
                            'search_method': 'rag'
                        }
                        formatted_results.append(formatted_result)
                        self.logger.debug(f"Added result for email {matched_email_id} with score {relevance_score:.3f}")
                    else:
                        self.logger.warning(f"❌ Could not match RAG result to an email in context")
                        self.logger.warning(f"📝 Content preview: {content[:200]}...")
                        self.logger.warning(f"📁 Document name: {document_name}")
                        self.logger.warning(f"🏷️ Metadata: {metadata}")
                        # Log available email IDs for debugging
                        self.logger.warning(f"📋 Available email IDs (first 5): {list(email_lookup.keys())[:5]}...")
                        
                        # Try to extract any UUID-like pattern from content
                        import re
                        uuid_pattern = r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
                        found_uuids = re.findall(uuid_pattern, content)
                        if found_uuids:
                            self.logger.warning(f"🔍 Found UUIDs in content: {found_uuids[:3]}...")
                            for uuid in found_uuids:
                                if uuid in email_lookup:
                                    self.logger.warning(f"🎯 UUID {uuid} found in email lookup! This should have been matched.")
                                    break
                
                # Log filtering summary
                total_rag_results = len(relevant_contents)
                filtered_count = total_rag_results - len(formatted_results)
                self.logger.info("=== FILTERING SUMMARY ===")
                self.logger.info(f"📊 RAG Retrieved: {total_rag_results} emails")
                self.logger.info(f"✅ Passed Filter: {len(formatted_results)} emails") 
                self.logger.info(f"🚫 Filtered Out: {filtered_count} emails")
                self.logger.info(f"📈 Filter Rate: {(filtered_count/total_rag_results*100):.1f}% removed")
                self.logger.info(f"🎯 Threshold Used: {dynamic_threshold:.4f} ({rag_system.config.min_relevance_score_percentage:.0%} of {max([result.get('score', 0.0) for result in relevant_contents]):.4f})")
                if formatted_results:
                    final_scores = [r.get('relevance_score', 0) for r in formatted_results]
                    self.logger.info(f"📋 Final Score Range: {min(final_scores):.4f} - {max(final_scores):.4f}")
                self.logger.info("=== END FILTERING ===")
                
                self.logger.info(f"Step 6 completed: Matched and formatted {len(formatted_results)} email results (after dynamic score filtering with threshold {dynamic_threshold:.3f})")
                
                search_time = time.time() - search_start_time
                return {
                    "success": True,
                    "results": formatted_results,
                    "search_method": "rag",
                    "total_searched": len(context_emails),
                    "total_matched": len(relevant_contents),
                    "results_after_filtering": len(formatted_results),
                    "dynamic_score_threshold": dynamic_threshold,
                    "highest_score": max([result.get("score", 0.0) for result in relevant_contents]) if relevant_contents else 0.0,
                    "score_threshold_percentage": rag_system.config.min_relevance_score_percentage,
                    "processing_time": search_time
                }
                
            except Exception as query_error:
                self.logger.error(f"Failed to query RAG system: {query_error}", exc_info=True)
                return {
                    "success": False,
                    "error": f"Failed to query emails: {str(query_error)}",
                    "results": [],
                    "search_method": "rag_error",
                    "total_searched": len(context_emails),
                    "processing_time": time.time() - search_start_time
                }
            
        except Exception as e:
            total_search_time = time.time() - search_start_time
            self.logger.error(f"Error in chatbot_intelligent_email_search with RAG: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Search failed: {str(e)}",
                "results": [],
                "search_method": "error",
                "total_searched": 0,
                "processing_time": total_search_time
            }


# Create a singleton instance of the email service
email_service = EmailService()

