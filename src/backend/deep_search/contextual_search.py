"""
Contextual Search Service for Email.

This module provides a contextual search approach that sends all retrieved emails
directly to the Albert API for intelligent search, bypassing the RAG system.
This approach:
1. Retrieves the most recent emails (up to 500)
2. Sends all emails as context to the Albert API
3. Uses the Albert API's intelligence to find relevant emails
4. Returns formatted results for mailbox display

This is useful when you want to leverage Albert's full capabilities without
the overhead of local embeddings and vector storage.
"""

import json
import time
import logging
import re
import html
from typing import Dict, List, Any
from django.contrib.auth import get_user_model

from core import models

try:
    from .email_utils import email_utils
except ImportError as e:
    print(f"Warning: Could not import email_utils: {e}")
    email_utils = None

logger = logging.getLogger(__name__)
User = get_user_model()


class ContextualSearchService:
    """
    Contextual search service for email.
    
    Provides Albert API-based contextual search functionality using shared email utilities.
    """
    
    def __init__(self):
        """Initialize the contextual search service."""
        self.logger = logger
        self.email_utils = email_utils
        if email_utils is None:
            self.logger.warning("email_utils not available, using fallback methods")
    
    def _get_user_accessible_mailboxes(self, user_id: str) -> List[models.Mailbox]:
        """
        Fallback method to get all mailboxes that a user has access to.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            List of Mailbox objects the user can access
        """
        try:
            self.logger.info(f"Getting accessible mailboxes for user_id: {user_id}")
            
            user = User.objects.get(id=user_id)
            self.logger.debug(f"Found user: {user.email if hasattr(user, 'email') else user}")
            
            mailboxes = models.Mailbox.objects.filter(
                accesses__user=user
            ).select_related('domain', 'contact').order_by("-created_at")
            
            mailbox_count = mailboxes.count()
            self.logger.info(f"Found {mailbox_count} accessible mailboxes for user {user}")
            
            if mailbox_count > 0:
                mailbox_list = list(mailboxes)
                self.logger.debug(f"Mailbox IDs: {[str(mb.id) for mb in mailbox_list[:5]]}")
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
    
    def _get_recent_messages(self, mailboxes: List[models.Mailbox], limit: int = 500) -> List[models.Message]:
        """
        Fallback method to get the most recent messages from the given mailboxes.
        
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
            self.logger.debug(f"Searching messages in mailbox IDs: {mailbox_ids[:5]}")
            
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
    
    def _get_parsed_message_content(self, message: models.Message) -> str:
        """
        Fallback method to get parsed text content from a message for chatbot processing.
        
        Args:
            message: Message object
            
        Returns:
            String containing the parsed text content
        """
        try:
            self.logger.debug(f"Parsing message {message.id} - {message.subject}")
            
            parsed_data = message.get_parsed_data()
            self.logger.debug(f"Parsed data keys: {list(parsed_data.keys())}")
            
            text_content = ""
            text_body = parsed_data.get('textBody', [])
            html_body = parsed_data.get('htmlBody', [])
            self.logger.debug(f"Text body parts: {len(text_body)}, HTML body parts: {len(html_body)}")
            
            if text_body:
                for text_part in text_body:
                    if isinstance(text_part, dict) and 'content' in text_part:
                        text_content += text_part['content'] + "\n"
                    elif isinstance(text_part, str):
                        text_content += text_part + "\n"
            
            if not text_content and html_body:
                self.logger.debug(f"No text body, extracting from HTML")
                for html_part in html_body:
                    if isinstance(html_part, dict) and 'content' in html_part:
                        html_content = html_part['content']
                        clean_text = re.sub(r'<[^>]+>', '', html_content)
                        clean_text = html.unescape(clean_text)
                        text_content += clean_text + "\n"
            
            text_content = text_content.strip()
            
            self.logger.debug(f"Extracted {len(text_content)} characters of text content")
            return text_content
            
        except Exception as e:
            self.logger.error(f"Error parsing message content for {message}: {e}", exc_info=True)
            return ""
    
    def _get_parsed_message_details(self, message: models.Message) -> Dict[str, Any]:
        """
        Fallback method to get parsed content details from a message using the model's built-in parsing methods.
        
        Args:
            message: Message object
            
        Returns:
            Dictionary with parsed message content and metadata
        """
        try:
            self.logger.debug(f"Parsing message details {message.id} - {message.subject}")
            
            parsed_data = message.get_parsed_data()
            self.logger.debug(f"Parsed data keys: {list(parsed_data.keys())}")
            
            text_body = parsed_data.get('textBody', [])
            html_body = parsed_data.get('htmlBody', [])
            self.logger.debug(f"Text body parts: {len(text_body)}, HTML body parts: {len(html_body)}")
            
            attachments = []
            for attachment in message.attachments.all():
                attachments.append({
                    'name': attachment.name,
                    'size': attachment.size,
                    'content_type': attachment.content_type,
                })
            self.logger.debug(f"Found {len(attachments)} attachments")
            
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
    
    def _get_email_context_for_chatbot(self, user_id: str) -> Dict[str, Any]:
        """
        Fallback method to gather email context for the chatbot.
        Gets the 500 most recent emails with all available information.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Dictionary containing email context and metadata
        """
        start_time = time.time()
        self.logger.info(f"Getting email context for chatbot (fallback) - user_id: {user_id}")
        
        try:
            # Step 1: Get accessible mailboxes
            self.logger.info("Step 1: Getting accessible mailboxes")
            mailboxes = self._get_user_accessible_mailboxes(user_id)
            
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
            recent_message_objects = self._get_recent_messages(mailboxes, limit=500)
            
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
                if i < 10:
                    self.logger.debug(f"Processing message {i+1}: ID={message.id}, subject={message.subject[:50]}...")
                
                parsed_details = self._get_parsed_message_details(message)
                text_content = self._get_parsed_message_content(message)
                
                attachments = []
                for attachment in message.attachments.all():
                    attachments.append({
                        'name': attachment.name,
                        'size': attachment.size,
                        'content_type': attachment.content_type,
                    })
                
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
            self.logger.error(f"Error in _get_email_context_for_chatbot for user {user_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Error retrieving email context: {str(e)}",
                "emails": [],
                "total_emails": 0,
                "mailbox_count": 0,
                "processing_time": processing_time
            }
    
    def format_emails_for_albert_context(self, emails: List[Dict[str, Any]]) -> str:
        """
        Format emails for Albert API context.
        
        Args:
            emails: List of email dictionaries
            
        Returns:
            Formatted string containing all emails for Albert API context
        """
        try:
            self.logger.info(f"Formatting {len(emails)} emails for Albert API context")
            
            context_parts = []
            context_parts.append("# EMAIL CONTEXT\n")
            context_parts.append(f"Total emails provided: {len(emails)}\n\n")
            
            for i, email in enumerate(emails, 1):
                context_parts.append(f"## EMAIL {i} (ID: {email['id']})\n")
                context_parts.append(f"**Subject:** {email.get('subject', 'No subject')}\n")
                context_parts.append(f"**From:** {email.get('sender', {}).get('name', '')} <{email.get('sender', {}).get('email', '')}>\n")
                
                # Add recipients
                recipients = email.get('recipients', {})
                if recipients.get('to'):
                    to_list = [f"{r.get('name', '')} <{r.get('email', '')}>" for r in recipients.get('to', [])]
                    context_parts.append(f"**To:** {', '.join(to_list)}\n")
                
                if recipients.get('cc'):
                    cc_list = [f"{r.get('name', '')} <{r.get('email', '')}>" for r in recipients.get('cc', [])]
                    context_parts.append(f"**CC:** {', '.join(cc_list)}\n")
                
                context_parts.append(f"**Date:** {email.get('sent_at', 'No date')}\n")
                context_parts.append(f"**Thread ID:** {email.get('thread_id', 'No thread')}\n")
                
                # Add flags
                flags = email.get('flags', {})
                status_flags = []
                if flags.get('is_unread'):
                    status_flags.append("UNREAD")
                if flags.get('is_starred'):
                    status_flags.append("STARRED")
                if flags.get('is_draft'):
                    status_flags.append("DRAFT")
                
                if status_flags:
                    context_parts.append(f"**Status:** {', '.join(status_flags)}\n")
                
                # Add attachments
                if email.get('attachment_count', 0) > 0:
                    attachments = email.get('attachments', [])
                    att_names = [att.get('name', 'Unknown') for att in attachments]
                    context_parts.append(f"**Attachments:** {', '.join(att_names)}\n")
                
                # Add content
                content = email.get('content', '').strip()
                if content:
                    # Truncate very long content to avoid API limits
                    if len(content) > 2000:
                        content = content[:2000] + "... [TRUNCATED]"
                    context_parts.append(f"**Content:**\n{content}\n")
                else:
                    context_parts.append("**Content:** [No content available]\n")
                
                context_parts.append("\n" + "="*50 + "\n\n")
            
            formatted_context = "".join(context_parts)
            self.logger.info(f"Formatted context length: {len(formatted_context)} characters")
            
            return formatted_context
            
        except Exception as e:
            self.logger.error(f"Error formatting emails for Albert context: {e}", exc_info=True)
            return f"Error formatting emails: {str(e)}"
    
    def create_albert_search_prompt(self, user_query: str, emails_context: str) -> str:
        """
        Create a prompt for Albert API to search emails.
        
        Args:
            user_query: User's search query
            emails_context: Formatted emails context
            
        Returns:
            Formatted prompt for Albert API
        """
        try:
            prompt = f"""You are an intelligent email search assistant. You have access to a user's email collection and need to find the most relevant emails based on their search query.

USER QUERY: "{user_query}"

TASK: Analyze the provided emails and return the most relevant ones that match the user's query. Consider:
- Subject line relevance
- Content relevance
- Sender relevance
- Date relevance (if mentioned in query)
- Context and semantic meaning

RESPONSE FORMAT: Return ONLY a JSON array of objects with this exact structure:
[
  {{
    "id": "email_id_here",
    "relevance_score": 0.95,
    "reason": "Brief explanation of why this email is relevant"
  }},
  {{
    "id": "email_id_here",
    "relevance_score": 0.87,
    "reason": "Brief explanation of why this email is relevant"
  }}
]

IMPORTANT GUIDELINES:
- Return maximum 10 most relevant emails
- Only include emails with relevance_score >= 0.5
- Sort by relevance_score (highest first)
- Use exact email IDs from the provided context
- Keep reasons brief but informative
- If no emails are relevant, return empty array []

{emails_context}

Now analyze these emails and return the most relevant ones for the query: "{user_query}"
"""
            
            self.logger.debug(f"Created Albert search prompt of length: {len(prompt)}")
            return prompt
            
        except Exception as e:
            self.logger.error(f"Error creating Albert search prompt: {e}", exc_info=True)
            return f"Error creating prompt: {str(e)}"
    
    def parse_albert_search_response(self, response: str, context_emails: List[Dict]) -> List[Dict[str, Any]]:
        """
        Parse Albert API response and format results for frontend.
        
        Args:
            response: Raw Albert API response
            context_emails: Original email context
            
        Returns:
            List of formatted search results
        """
        try:
            self.logger.info(f"Parsing Albert search response (length: {len(response)})")
            
            # Create email lookup
            email_lookup = {email['id']: email for email in context_emails}
            self.logger.debug(f"Created email lookup with {len(email_lookup)} emails")
            
            # Try to extract JSON from response
            try:
                # Look for JSON array in the response
                import re
                json_match = re.search(r'\[.*?\]', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    self.logger.debug(f"Found JSON string: {json_str[:200]}...")
                    albert_results = json.loads(json_str)
                    self.logger.info(f"Successfully parsed {len(albert_results)} results from Albert")
                    
                    # Log the structure of the first result for debugging
                    if albert_results:
                        first_result = albert_results[0]
                        self.logger.debug(f"First result structure: {first_result}")
                        required_keys = ['id', 'relevance_score', 'reason']
                        missing_keys = [key for key in required_keys if key not in first_result]
                        if missing_keys:
                            self.logger.warning(f"First result missing keys: {missing_keys}")
                        
                else:
                    self.logger.warning("No JSON array found in Albert response")
                    self.logger.warning(f"Response content: {response[:500]}...")
                    
                    # Try to find any JSON-like structure
                    json_bracket_match = re.search(r'\{.*?\}', response, re.DOTALL)
                    if json_bracket_match:
                        self.logger.info("Found JSON object instead of array, attempting to parse...")
                        json_str = json_bracket_match.group(0)
                        try:
                            single_result = json.loads(json_str)
                            albert_results = [single_result]  # Wrap in array
                            self.logger.info(f"Successfully parsed single result as array")
                        except json.JSONDecodeError:
                            self.logger.warning("Failed to parse JSON object as well")
                            return []
                    else:
                        self.logger.warning("No JSON structure found in response at all")
                        return []
                    
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON from Albert response: {e}")
                self.logger.error(f"Failed JSON: {json_str if 'json_str' in locals() else 'No JSON string'}")
                return []
            
            # Format results for frontend
            formatted_results = []
            
            for i, result in enumerate(albert_results):
                self.logger.debug(f"Processing result {i+1}: {result}")
                
                email_id = result.get('id', '')
                relevance_score = result.get('relevance_score', 0.0)
                reason = result.get('reason', 'Albert identified as relevant')
                
                if not email_id:
                    self.logger.warning(f"Result {i+1} has no 'id' field: {result}")
                    continue
                
                if email_id in email_lookup:
                    email = email_lookup[email_id]
                    
                    # Format result for frontend compatibility
                    formatted_result = {
                        'id': email_id,
                        'message_id': email_id,
                        'thread_id': email.get('thread_id', ''),
                        'subject': email.get('subject', ''),
                        'from': email.get('sender', {}).get('email', ''),
                        'sender': {
                            'email': email.get('sender', {}).get('email', ''),
                            'name': email.get('sender', {}).get('name', '')
                        },
                        'sender_name': email.get('sender', {}).get('name', ''),
                        'sender_email': email.get('sender', {}).get('email', ''),
                        'date': email.get('sent_at'),
                        'sent_at': email.get('sent_at'),
                        'snippet': email.get('content', '')[:200] if email.get('content') else '',
                        'is_unread': email.get('flags', {}).get('is_unread', False),
                        'is_starred': email.get('flags', {}).get('is_starred', False),
                        'thread_subject': email.get('thread_subject', ''),
                        'relevance_score': relevance_score,
                        'ai_reason': reason,
                        'attachment_count': email.get('attachment_count', 0),
                        'content_preview': email.get('content', '')[:200] if email.get('content') else '',
                        'search_method': 'contextual_search'
                    }
                    
                    formatted_results.append(formatted_result)
                    self.logger.debug(f"✅ Added result for email {email_id} with score {relevance_score}")
                else:
                    self.logger.warning(f"❌ Albert returned email ID {email_id} not found in context")
                    self.logger.warning(f"Available email IDs (first 5): {list(email_lookup.keys())[:5]}")
            
            # Sort by relevance score (highest first)
            formatted_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            self.logger.info(f"Successfully parsed {len(formatted_results)} email results from Albert")
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Error parsing Albert search response: {e}", exc_info=True)
            self.logger.error(f"Response that caused error: {response[:500]}...")
            return []
    
    def chatbot_contextual_email_search(
        self, 
        user_id: str, 
        user_query: str, 
        api_client,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Perform intelligent email search using Albert API directly.
        
        This method:
        1. Retrieves the most recent emails (up to 500)
        2. Formats all emails as context for Albert API
        3. Sends the query and context to Albert API
        4. Parses and formats the results for frontend
        
        Args:
            user_id: UUID of the user
            user_query: User's natural language search query
            api_client: Albert API client instance
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary containing search results and metadata
        """
        search_start_time = time.time()
        self.logger.info(f"Starting contextual email search - user_id: {user_id}, query: '{user_query[:100]}...'")
        self.logger.info(f"API client type: {type(api_client)}")
        self.logger.info(f"Max results requested: {max_results}")
        
        try:
            # Step 1: Get all email context
            self.logger.info("Step 1: Fetching email context")
            
            if self.email_utils is None:
                self.logger.info("Using fallback email context method")
                context_result = self._get_email_context_for_chatbot(user_id)
            else:
                self.logger.info("Using email_utils for email context")
                context_result = self.email_utils.get_email_context_for_chatbot(user_id)
            
            self.logger.info(f"Successfully obtained email context")
            
            if not context_result["success"]:
                self.logger.error(f"Failed to get email context: {context_result.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": f"Failed to retrieve emails: {context_result.get('error', 'Unknown error')}",
                    "results": [],
                    "search_method": "contextual_search",
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
                    "search_method": "contextual_search",
                    "total_searched": 0,
                    "processing_time": time.time() - search_start_time
                }
            
            # Step 2: Format emails for Albert API context
            self.logger.info("Step 2: Formatting emails for Albert API context")
            
            # Limit emails to avoid API payload limits
            max_emails_for_context = min(100, len(context_emails))  # Limit to 100 emails for API
            emails_for_context = context_emails[:max_emails_for_context]
            
            emails_context = self.format_emails_for_albert_context(emails_for_context)
            self.logger.info(f"Step 2 completed: Formatted {len(emails_for_context)} emails for Albert context")
            
            # Step 3: Create Albert search prompt
            self.logger.info("Step 3: Creating Albert search prompt")
            search_prompt = self.create_albert_search_prompt(user_query, emails_context)
            self.logger.info(f"Step 3 completed: Created search prompt of length {len(search_prompt)}")
            
            # Step 4: Send query to Albert API
            self.logger.info("Step 4: Sending search query to Albert API")
            try:
                albert_start_time = time.time()
                
                # Prepare messages for Albert API (it expects a list of message objects)
                messages = [
                    {
                        "role": "user",
                        "content": search_prompt
                    }
                ]
                
                self.logger.info(f"Prepared {len(messages)} messages for Albert API")
                self.logger.debug(f"Message content length: {len(search_prompt)} characters")
                
                # Call Albert API using the correct method
                albert_response = api_client.make_request(messages)
                
                albert_time = time.time() - albert_start_time
                self.logger.info(f"Step 4 completed: Received Albert response in {albert_time:.2f}s")
                
                # Log the response structure for debugging
                self.logger.debug(f"Albert API response keys: {list(albert_response.keys()) if albert_response else 'None'}")
                
                # Extract content from Albert API response
                # The response structure is typically: {"choices": [{"message": {"content": "..."}}]}
                albert_content = ""
                if albert_response and "choices" in albert_response and len(albert_response["choices"]) > 0:
                    choice = albert_response["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        albert_content = choice["message"]["content"]
                        self.logger.info(f"Successfully extracted content from Albert response: {len(albert_content)} characters")
                    else:
                        self.logger.error(f"Unexpected choice structure in Albert response: {choice}")
                        return {
                            "success": False,
                            "error": "Invalid Albert API response structure - missing message content",
                            "results": [],
                            "search_method": "contextual_search",
                            "total_searched": len(context_emails),
                            "processing_time": time.time() - search_start_time
                        }
                else:
                    self.logger.error(f"Invalid Albert API response structure: {albert_response}")
                    return {
                        "success": False,
                        "error": "Invalid Albert API response structure - missing choices",
                        "results": [],
                        "search_method": "contextual_search",
                        "total_searched": len(context_emails),
                        "processing_time": time.time() - search_start_time
                    }
                
                if not albert_content:
                    self.logger.error("No content received from Albert API")
                    return {
                        "success": False,
                        "error": "No content received from Albert API",
                        "results": [],
                        "search_method": "contextual_search",
                        "total_searched": len(context_emails),
                        "processing_time": time.time() - search_start_time
                    }
                
                self.logger.debug(f"Albert response content: {albert_content[:500]}...")
                
            except Exception as api_error:
                self.logger.error(f"Error calling Albert API: {api_error}", exc_info=True)
                self.logger.error(f"API client type: {type(api_client)}")
                self.logger.error(f"API client methods: {[method for method in dir(api_client) if not method.startswith('_')]}")
                return {
                    "success": False,
                    "error": f"Failed to call Albert API: {str(api_error)}",
                    "results": [],
                    "search_method": "contextual_search",
                    "total_searched": len(context_emails),
                    "processing_time": time.time() - search_start_time
                }
            
            # Step 5: Parse Albert response and format results
            self.logger.info("Step 5: Parsing Albert response and formatting results")
            
            # Log the full Albert response for debugging
            self.logger.info(f"Albert API returned content of length: {len(albert_content)}")
            self.logger.debug(f"First 500 characters of Albert response: {albert_content[:500]}")
            
            formatted_results = self.parse_albert_search_response(albert_content, context_emails)
            
            self.logger.info(f"Parsed {len(formatted_results)} results from Albert response")
            
            # Apply max_results limit
            if len(formatted_results) > max_results:
                formatted_results = formatted_results[:max_results]
                self.logger.info(f"Limited results to {max_results} as requested")
            
            self.logger.info(f"Step 5 completed: Formatted {len(formatted_results)} search results")
            
            # Log detailed information about the final results
            if formatted_results:
                self.logger.info("=== CONTEXTUAL SEARCH RESULTS ===")
                for i, result in enumerate(formatted_results[:5]):  # Log first 5 results
                    self.logger.info(f"  #{i+1}: ID={result.get('id', 'N/A')[:8]}... | Score={result.get('relevance_score', 'N/A')} | Subject={result.get('subject', 'N/A')[:50]}...")
                if len(formatted_results) > 5:
                    self.logger.info(f"  ... and {len(formatted_results) - 5} more results")
                self.logger.info("=== END CONTEXTUAL SEARCH RESULTS ===")
            else:
                self.logger.warning("No results were formatted from Albert response")
                self.logger.warning(f"Raw Albert content preview: {albert_content[:200]}...")
            
            search_time = time.time() - search_start_time
            
            return {
                "success": True,
                "results": formatted_results,
                "search_method": "contextual_search",
                "total_searched": len(context_emails),
                "emails_sent_to_albert": len(emails_for_context),
                "processing_time": search_time,
                "albert_processing_time": albert_time if 'albert_time' in locals() else 0
            }
            
        except Exception as e:
            total_search_time = time.time() - search_start_time
            self.logger.error(f"Error in chatbot_contextual_email_search: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Search failed: {str(e)}",
                "results": [],
                "search_method": "contextual_search",
                "total_searched": 0,
                "processing_time": total_search_time
            }


# Create a singleton instance of the contextual search service
contextual_search_service = ContextualSearchService()
