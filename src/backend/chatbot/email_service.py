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
from typing import Dict, List, Optional, Any
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils import timezone

from core import models

logger = logging.getLogger(__name__)
User = get_user_model()


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
        Perform intelligent email search using Albert API with optimized email summaries.
        Uses a more efficient approach by sending email summaries instead of full content.
        
        Args:
            user_id: UUID of the user
            user_query: User's natural language search query
            api_client: Albert API client instance
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary containing search results and metadata
        """
        search_start_time = time.time()
        self.logger.info(f"Starting intelligent email search - user_id: {user_id}, query: '{user_query[:100]}...'")
        
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
            
            # Step 2: Create optimized email summaries for AI (limit content size)
            self.logger.info("Step 2: Creating optimized email summaries for AI")
            
            emails_for_ai = []
            for email in context_emails:
                # Truncate content to avoid huge payloads
                content = email.get('content', '')
                content_preview = content[:300] if content else ''  # Limit to 300 chars
                
                email_summary = {
                    'id': email['id'],
                    'subject': email.get('subject', '')[:200],  # Limit subject length
                    'content_preview': content_preview,
                    'sender_name': email.get('sender', {}).get('name', '')[:100],
                    'sender_email': email.get('sender', {}).get('email', ''),
                    'sent_at': email.get('sent_at', ''),
                    'attachment_count': email.get('attachment_count', 0),
                    'has_attachments': email.get('attachment_count', 0) > 0,
                    'attachment_names': [att.get('name', '')[:50] for att in email.get('attachments', [])][:3],  # First 3 attachment names
                    'is_unread': email.get('flags', {}).get('is_unread', False),
                    'is_starred': email.get('flags', {}).get('is_starred', False),
                }
                emails_for_ai.append(email_summary)
            
            # Step 3: Create a more concise search prompt
            self.logger.info("Step 3: Creating optimized AI search prompt")
            
            search_prompt = f"""Find relevant emails for this query: "{user_query}"

I have {len(emails_for_ai)} emails to search. Here are email summaries:

{chr(10).join([f"ID: {email['id']}, Subject: {email['subject']}, From: {email['sender_name']} <{email['sender_email']}>, Attachments: {email['attachment_count']}, Content: {email['content_preview'][:100]}..." for email in emails_for_ai[:50]])}

{"[Note: Showing first 50 of " + str(len(emails_for_ai)) + " emails]" if len(emails_for_ai) > 50 else ""}

Return a JSON array of relevant email IDs with relevance scores:
[{{"id": "email_id", "relevance_score": 0.95, "reason": "why relevant"}}]

Instructions:
- For attachment queries: prioritize emails with attachment_count > 0
- For sender queries: match sender_name or sender_email
- For content queries: search subject and content_preview
- Maximum {max_results} results
- Only genuinely relevant emails
- Return empty array [] if no relevant emails"""
            
            prompt_length = len(search_prompt)
            self.logger.info(f"Step 3 completed: Prepared optimized AI prompt (length: {prompt_length} chars)")
            
            # Step 4: Call Albert API with smaller payload
            self.logger.info("Step 4: Calling Albert API with optimized prompt")
            ai_start_time = time.time()
            
            try:
                self.logger.debug("Calling Albert API...")
                
                # Format the prompt as messages for the API
                messages = [
                    {
                        "role": "user",
                        "content": search_prompt
                    }
                ]
                
                ai_response = api_client.make_request(messages=messages)
                ai_processing_time = time.time() - ai_start_time
                
                self.logger.info(f"Albert API call completed in {ai_processing_time:.2f}s")
                self.logger.info(f"Albert API response type: {type(ai_response)}")
                self.logger.info(f"Albert API response keys: {list(ai_response.keys()) if isinstance(ai_response, dict) else 'Not a dict'}")
                self.logger.info(f"Albert API response: {ai_response}")
                
                # Extract content from API response
                if ai_response and ai_response.get("choices") and len(ai_response["choices"]) > 0:
                    ai_content = ai_response["choices"][0].get("message", {}).get("content", "")
                    self.logger.info(f"AI response received (length: {len(ai_content)} chars)")
                    self.logger.info(f"AI response content preview: {ai_content[:1000]}")  # Log full content preview at INFO level
                    
                    # Step 5: Parse AI response
                    self.logger.info("Step 5: Parsing AI response")
                    self.logger.info(f"Full AI content to parse: {ai_content}")  # Log full content for debugging
                    parsed_results = self.parse_ai_response_for_email_search(ai_content, context_emails)
                    self.logger.info(f"Parsing completed: Found {len(parsed_results) if parsed_results else 0} results")
                    
                    if parsed_results:
                        search_time = time.time() - search_start_time
                        self.logger.info(f"AI search successful: Found {len(parsed_results)} relevant emails in {search_time:.2f}s")
                        return {
                            "success": True,
                            "results": parsed_results,
                            "search_method": "ai_optimized",
                            "total_searched": len(context_emails),
                            "emails_sent_to_ai": min(50, len(context_emails)),
                            "ai_processing_time": ai_processing_time,
                            "processing_time": search_time
                        }
                    else:
                        self.logger.warning("AI response was parsed but returned no results")
                        return {
                            "success": True,
                            "results": [],
                            "message": "No relevant emails found",
                            "search_method": "ai_optimized",
                            "total_searched": len(context_emails),
                            "emails_sent_to_ai": min(50, len(context_emails)),
                            "ai_processing_time": ai_processing_time,
                            "processing_time": time.time() - search_start_time
                        }
                else:
                    self.logger.warning(f"Albert API returned no valid response structure")
                    self.logger.warning(f"Raw Albert API response: {ai_response}")
                    self.logger.warning(f"Response type: {type(ai_response)}")
                    if ai_response:
                        self.logger.warning(f"Response keys: {list(ai_response.keys()) if isinstance(ai_response, dict) else 'Not a dict'}")
                        if isinstance(ai_response, dict):
                            self.logger.warning(f"Choices field: {ai_response.get('choices', 'No choices field')}")
                            if 'choices' in ai_response and ai_response['choices']:
                                self.logger.warning(f"First choice: {ai_response['choices'][0] if len(ai_response['choices']) > 0 else 'No first choice'}")
                    return {
                        "success": False,
                        "error": "Albert API returned no valid response",
                        "results": [],
                        "search_method": "ai_error",
                        "total_searched": len(context_emails),
                        "processing_time": time.time() - search_start_time
                    }
                    
            except Exception as ai_error:
                ai_processing_time = time.time() - ai_start_time
                self.logger.error(f"Albert API call failed after {ai_processing_time:.2f}s: {ai_error}", exc_info=True)
                return {
                    "success": False,
                    "error": f"Albert API call failed: {str(ai_error)}",
                    "results": [],
                    "search_method": "ai_error",
                    "total_searched": len(context_emails),
                    "processing_time": time.time() - search_start_time
                }
            
        except Exception as e:
            total_search_time = time.time() - search_start_time
            self.logger.error(f"Error in chatbot_intelligent_email_search: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Search failed: {str(e)}",
                "results": [],
                "search_method": "error",
                "total_searched": 0,
                "processing_time": total_search_time
            }

