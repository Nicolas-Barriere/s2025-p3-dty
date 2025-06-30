"""
Function executor for email-related operations.

This module handles the execution of email functions called by the Albert API.
"""

import json
import time
import logging
from typing import Dict, Any

from .exceptions import FunctionExecutionError, UserNotFoundError
from .email_processor import EmailProcessor

logger = logging.getLogger(__name__)


class FunctionExecutor:
    """Executes email-related functions for the chatbot."""
    
    def __init__(self, email_processor: EmailProcessor):
        """
        Initialize the function executor.
        
        Args:
            email_processor: Email processor instance
        """
        self.email_processor = email_processor
    
    def execute_function(self, function_name: str, arguments: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        """
        Execute an email-related function with the provided arguments.
        
        Args:
            function_name: Name of the function to execute
            arguments: Arguments for the function
            user_id: ID of the user making the request
            
        Returns:
            Dictionary containing the function execution result
        """
        try:
            logger.info(f"🔧 Executing function: {function_name}")
            logger.info(f"👤 User ID: {user_id}")
            self._log_function_arguments(arguments)
            
            execution_start_time = time.time()
            
            # Route to appropriate handler
            if function_name == "summarize_email":
                return self._handle_summarize_email(arguments, user_id, execution_start_time)
            elif function_name == "generate_email_reply":
                return self._handle_generate_email_reply(arguments, user_id, execution_start_time)
            elif function_name == "classify_email":
                return self._handle_classify_email(arguments, user_id, execution_start_time)
            elif function_name in ["search_emails", "search_threads", "get_recent_emails", 
                                   "get_unread_emails", "get_user_mailboxes", "get_thread_statistics",
                                   "retrieve_email_content"]:
                return self._handle_retrieval_function(function_name, arguments, user_id, execution_start_time)
            elif function_name in ["create_draft_email", "send_email", "reply_to_email", 
                                   "forward_email", "delete_draft"]:
                return self._handle_writing_function(function_name, arguments, user_id, execution_start_time)
            else:
                return self._handle_unknown_function(function_name, execution_start_time)
                
        except Exception as e:
            execution_time = time.time() - execution_start_time
            logger.error(f"❌ Function execution failed: {function_name} (took {execution_time:.2f}s)")
            logger.error(f"💥 Error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "function": function_name,
                "arguments": arguments,
                "execution_time": execution_time
            }
    
    def _log_function_arguments(self, arguments: Dict[str, Any]) -> None:
        """Log function arguments for debugging."""
        logger.info(f"📝 Function arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}")
        
        for key, value in arguments.items():
            value_type = type(value).__name__
            if isinstance(value, str):
                value_preview = value[:100] + "..." if len(value) > 100 else value
                logger.debug(f"  - {key} ({value_type}): {value_preview}")
            elif isinstance(value, (list, dict)):
                logger.debug(f"  - {key} ({value_type}): {len(value)} items")
            else:
                logger.debug(f"  - {key} ({value_type}): {value}")
    
    def _handle_summarize_email(self, arguments: Dict[str, Any], user_id: str, start_time: float) -> Dict[str, Any]:
        """Handle email summarization function."""
        email_content = arguments.get("email_content", "")
        sender = arguments.get("sender", "")
        subject = arguments.get("subject", "")
        query = arguments.get("query", "")
        
        # Automatically retrieve email if query is provided
        retrieve_email = bool(query)
        
        logger.info(f"📧 summarize_email - query: '{query}', retrieve_email: {retrieve_email}, email_content length: {len(email_content)}")
        
        # If query is provided, fetch the email content first
        if retrieve_email:
            if not user_id:
                return {"success": False, "error": "User ID required for email retrieval", "function": "summarize_email"}
            
            email_content, sender, subject = self._retrieve_email_content(
                user_id, query, sender, subject, start_time
            )
            if email_content is None:
                return {"success": False, "error": "Failed to retrieve email", "function": "summarize_email"}
        
        result = self.email_processor.summarize_mail(email_content, sender, subject)
        execution_time = time.time() - start_time
        
        if result.get('success'):
            logger.info(f"✅ summarize_email completed successfully (took {execution_time:.2f}s)")
            return {
                "success": True,
                "function": "summarize_email",
                "result": result,
                "execution_time": execution_time
            }
        else:
            logger.warning(f"⚠️ summarize_email failed (took {execution_time:.2f}s): {result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "function": "summarize_email",
                "error": result.get('error', 'Error in summarize_mail'),
                "result": result,
                "execution_time": execution_time
            }
    
    def _handle_generate_email_reply(self, arguments: Dict[str, Any], user_id: str, start_time: float) -> Dict[str, Any]:
        """Handle email reply generation function."""
        original_email = arguments.get("original_email", "")
        context = arguments.get("context", "")
        tone = arguments.get("tone", "professional")
        query = arguments.get("query", "")
        sender = arguments.get("sender", "")
        subject = arguments.get("subject", "")
        
        # Automatically retrieve email if query is provided
        retrieve_email = bool(query)
        
        logger.info(f"✉️ generate_email_reply - query: '{query}', retrieve_email: {retrieve_email}, tone: '{tone}'")
        
        # If query is provided, fetch the email content first
        retrieved_metadata = None
        if retrieve_email:
            if not user_id:
                return {"success": False, "error": "User ID required for email retrieval", "function": "generate_email_reply"}
            
            # Get email content and metadata for draft creation
            from .email_retrieval import retrieve_email_content_by_query
            retrieval_result = retrieve_email_content_by_query(
                user_id=user_id, 
                query=query, 
                limit=1,
                use_elasticsearch=True
            )
            
            if not retrieval_result.get('success'):
                return {"success": False, "error": "Failed to retrieve email", "function": "generate_email_reply"}
            
            original_email = retrieval_result.get('email_content', '')
            retrieved_metadata = retrieval_result.get('metadata', {})
        
        # Determine if we should create a draft based on the arguments
        create_draft = arguments.get("create_draft", False)
        
        result = self.email_processor.generate_mail_answer(
            original_email, 
            context, 
            tone,
            create_draft=create_draft,
            user_id=user_id if create_draft else None,
            original_message_metadata=retrieved_metadata
        )
        execution_time = time.time() - start_time
        
        if result.get('success'):
            logger.info(f"✅ generate_email_reply completed successfully (took {execution_time:.2f}s)")
            return {
                "success": True,
                "function": "generate_email_reply", 
                "result": result,
                "execution_time": execution_time
            }
        else:
            logger.warning(f"⚠️ generate_email_reply failed (took {execution_time:.2f}s): {result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "function": "generate_email_reply",
                "error": result.get('error', 'Error in generate_mail_answer'),
                "result": result,
                "execution_time": execution_time
            }
    
    def _handle_classify_email(self, arguments: Dict[str, Any], user_id: str, start_time: float) -> Dict[str, Any]:
        """Handle email classification function."""
        email_content = arguments.get("email_content", "")
        sender = arguments.get("sender", "")
        subject = arguments.get("subject", "")
        query = arguments.get("query", "")
        
        # Automatically retrieve email if query is provided
        retrieve_email = bool(query)
        
        logger.info(f"🏷️ classify_email - query: '{query}', retrieve_email: {retrieve_email}, sender: '{sender}'")
        
        # If query is provided, fetch the email content first
        if retrieve_email:
            if not user_id:
                return {"success": False, "error": "User ID required for email retrieval", "function": "classify_email"}
            
            email_content, sender, subject = self._retrieve_email_content(
                user_id, query, sender, subject, start_time
            )
            if email_content is None:
                return {"success": False, "error": "Failed to retrieve email", "function": "classify_email"}
        
        result = self.email_processor.classify_mail(email_content, sender, subject)
        execution_time = time.time() - start_time
        
        if result.get('success'):
            logger.info(f"✅ classify_email completed successfully (took {execution_time:.2f}s)")
            return {
                "success": True,
                "function": "classify_email",
                "result": result,
                "execution_time": execution_time
            }
        else:
            logger.warning(f"⚠️ classify_email failed (took {execution_time:.2f}s): {result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "function": "classify_email",
                "error": result.get('error', 'Error in classify_mail'),
                "result": result,
                "execution_time": execution_time
            }
    
    def _handle_retrieval_function(self, function_name: str, arguments: Dict[str, Any], user_id: str, start_time: float) -> Dict[str, Any]:
        """Handle email retrieval functions."""
        if not user_id:
            return {"success": False, "error": "User ID required for email operations"}
        
        try:
            if function_name == "search_emails":
                from .email_retrieval import search_messages
                query = arguments.get("query", "")
                mailbox_id = arguments.get("mailbox_id")
                limit = arguments.get("limit", 10)
                use_elasticsearch = arguments.get("use_elasticsearch", True)
                
                results = search_messages(user_id, query, mailbox_id, limit, use_elasticsearch=use_elasticsearch)
                return {
                    "success": True,
                    "function": function_name,
                    "result": {"emails": results, "count": len(results)}
                }
            
            elif function_name == "get_recent_emails":
                from .email_retrieval import get_recent_messages
                days = arguments.get("days", 7)
                limit = arguments.get("limit", 10)
                
                results = get_recent_messages(user_id, days, limit)
                return {
                    "success": True,
                    "function": function_name,
                    "result": {"emails": results, "count": len(results)}
                }
            
            elif function_name == "retrieve_email_content":
                from .email_retrieval import retrieve_email_content_by_query
                query = arguments.get("query", "")
                limit = arguments.get("limit", 5)
                use_elasticsearch = arguments.get("use_elasticsearch", True)
                
                result = retrieve_email_content_by_query(user_id, query, limit, use_elasticsearch)
                return {
                    "success": True,
                    "function": function_name,
                    "result": result
                }
            
            # Add other retrieval functions as needed
            else:
                return {"success": False, "error": f"Retrieval function {function_name} not implemented"}
                
        except Exception as e:
            logger.error(f"Error in retrieval function {function_name}: {e}")
            return {"success": False, "error": f"Error in {function_name}: {str(e)}"}
    
    def _handle_writing_function(self, function_name: str, arguments: Dict[str, Any], user_id: str, start_time: float) -> Dict[str, Any]:
        """Handle email writing functions."""
        if not user_id:
            return {"success": False, "error": "User ID required for email operations"}
        
        try:
            if function_name == "create_draft_email":
                from .email_writer import create_draft_email, get_user_mailboxes
                
                subject = arguments.get("subject", "")
                body = arguments.get("body", "")
                recipients_to = arguments.get("recipients_to", [])
                recipients_cc = arguments.get("recipients_cc", [])
                recipients_bcc = arguments.get("recipients_bcc", [])
                mailbox_id = arguments.get("mailbox_id")
                
                # Get mailbox if not specified
                if not mailbox_id:
                    user_mailboxes = get_user_mailboxes(user_id)
                    if not user_mailboxes:
                        return {"success": False, "error": "No accessible mailboxes found"}
                    
                    sender_mailbox = next((mb for mb in user_mailboxes if mb.get('can_send', False)), None)
                    if not sender_mailbox:
                        return {"success": False, "error": "No mailboxes with send permissions found"}
                    
                    mailbox_id = sender_mailbox['id']
                
                result = create_draft_email(
                    user_id, mailbox_id, subject, body, 
                    recipients_to, recipients_cc, recipients_bcc
                )
                return {
                    "success": True,
                    "function": function_name,
                    "result": result
                }
            
            # Add other writing functions as needed
            else:
                return {"success": False, "error": f"Writing function {function_name} not implemented"}
                
        except Exception as e:
            logger.error(f"Error in writing function {function_name}: {e}")
            return {"success": False, "error": f"Error in {function_name}: {str(e)}"}
    
    def _handle_unknown_function(self, function_name: str, start_time: float) -> Dict[str, Any]:
        """Handle unknown function calls."""
        logger.warning(f"❌ Unknown function requested: {function_name}")
        return {
            "success": False,
            "error": f"Unknown function: {function_name}"
        }
    
    def _retrieve_email_content(self, user_id: str, query: str, sender: str, subject: str, start_time: float) -> tuple:
        """
        Retrieve email content using search query or sender/subject.
        
        Returns:
            Tuple of (email_content, sender, subject) or (None, None, None) if failed
        """
        try:
            logger.info(f"🔍 Retrieving email with query: '{query}'")
            
            if not query:
                # Build search query from sender and subject if not provided
                search_parts = []
                if sender:
                    search_parts.append(sender)
                if subject:
                    search_parts.append(subject)
                query = " ".join(search_parts)
                logger.info(f"🔍 Built search query from sender/subject: '{query}'")
            
            if not query:
                logger.error("No search query provided and cannot build one from sender/subject")
                return None, None, None
            
            # Retrieve the email content
            from .email_retrieval import retrieve_email_content_by_query
            
            retrieval_result = retrieve_email_content_by_query(
                user_id=user_id, 
                query=query, 
                limit=1,
                use_elasticsearch=True
            )
            
            if not retrieval_result.get('success'):
                logger.warning(f"⚠️ Failed to retrieve email: {retrieval_result.get('error')}")
                return None, None, None
            
            # Use the retrieved email content
            email_content = retrieval_result.get('email_content', '')
            retrieved_metadata = retrieval_result.get('metadata', {})
            
            # Update sender and subject from retrieved metadata if not provided
            if not sender:
                sender = retrieved_metadata.get('sender_name', '')
            if not subject:
                subject = retrieved_metadata.get('subject', '')
            
            logger.info(f"📧 Retrieved email content ({len(email_content)} chars) from '{sender}' with subject '{subject}'")
            return email_content, sender, subject
            
        except Exception as e:
            logger.error(f"Error retrieving email content: {e}")
            return None, None, None
