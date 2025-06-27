"""
Conversation handler for the chatbot.

This module manages conversational interactions and multi-step function calling.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any

from .api_client import AlbertAPIClient
from .config import AlbertConfig
from .function_executor import FunctionExecutor
from .response_formatter import ResponseFormatter
from .tools import EmailToolsDefinition

logger = logging.getLogger(__name__)


class ConversationHandler:
    """Handles conversational interactions and function calling."""
    
    def __init__(self, api_client: AlbertAPIClient, function_executor: FunctionExecutor):
        """
        Initialize the conversation handler.
        
        Args:
            api_client: Albert API client instance
            function_executor: Function executor instance
        """
        self.api_client = api_client
        self.function_executor = function_executor
        self.response_formatter = ResponseFormatter()
        self.tools_definition = EmailToolsDefinition()
    
    def chat_conversation(self, user_message: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Handle conversational chat with the user.
        
        Args:
            user_message: The user's message
            conversation_history: Previous conversation messages (optional)
            
        Returns:
            Dictionary containing the conversational response
        """
        try:
            logger.info("Generating conversational response")
            
            if conversation_history is None:
                conversation_history = []
            
            system_prompt = """
            Tu es un assistant intelligent et amical spécialisé dans la gestion d'emails. Tu peux aider les utilisateurs avec:
            - La gestion et l'organisation de leurs emails
            - La rédaction de réponses professionnelles
            - L'analyse et le résumé de contenu d'emails
            - Des conseils sur la communication par email
            - Des questions générales liées à la productivité

            Réponds toujours en français de manière claire, utile et engageante. Si l'utilisateur semble vouloir effectuer une action spécifique sur un email (résumer, répondre, classer), guide-le gentiment.
            """
            
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_message})
            
            response = self.api_client.make_request(messages)
            
            # Extract response content
            choice = response.get('choices', [{}])[0]
            message = choice.get('message', {})
            content = message.get('content', '')
            if content:
                content = content.strip()
            
            if content:
                logger.info("Successfully generated conversational response")
                return {
                    'success': True,
                    'response': content,
                    'type': 'conversation'
                }
            
            logger.warning("No content in conversational response")
            return {
                'success': True,
                'response': 'Je suis désolé, je n\'ai pas pu générer une réponse appropriée. Pouvez-vous reformuler votre question ?',
                'type': 'conversation'
            }
            
        except Exception as e:
            logger.error(f"Error in conversational chat: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': 'Une erreur s\'est produite. Comment puis-je vous aider autrement ?',
                'type': 'conversation'
            }
    
    def process_user_message(self, user_message: str, user_id: str = None, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Main entry point for processing user messages with function calling.
        
        Args:
            user_message: The user's input message
            user_id: User ID for email operations (optional)
            conversation_history: Previous conversation messages (optional)
            
        Returns:
            Dictionary containing the appropriate response based on function calls
        """
        try:
            logger.info(f"Processing user message: user_id={user_id}, message='{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
            
            if conversation_history is None:
                conversation_history = []
            
            # Use unified function calling handler
            return self._handle_function_calls(user_message, user_id, conversation_history)
            
        except Exception as e:
            logger.error(f"Error processing user message: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': 'Une erreur s\'est produite lors du traitement de votre message. Comment puis-je vous aider autrement ?',
                'type': 'error'
            }
    
    def _handle_function_calls(self, user_message: str, user_id: str = None, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Unified function calling handler that supports both single and multi-step operations.
        
        Args:
            user_message: The user's input message
            user_id: User ID for email operations
            conversation_history: Previous conversation messages
            
        Returns:
            Dictionary containing the response after function execution
        """
        try:
            logger.info("🚀 Starting unified function calling handler")
            
            # Enhanced system prompt for intelligent function calling with updated workflows
            system_prompt = """
            Tu es un assistant intelligent spécialisé dans la gestion d'emails avec des capacités de fonction calling avancées.
            
            WORKFLOWS INTELLIGENTS (emails récupérés automatiquement):
            
            🎯 ACTIONS DIRECTES (pas besoin de retrieve_email_content):
            
            1. "Résume l'email de [personne] sur [sujet]":
               → summarize_email(query="personne sujet") 
               ❌ PAS retrieve_email_content d'abord !
            
            2. "Classifie l'email de [personne]":
               → classify_email(query="personne")
               ❌ PAS retrieve_email_content d'abord !
            
            3. "Réponds à l'email de [personne]":
               → generate_email_reply(query="personne")
               → create_draft_email(body=réponse_générée)
            
            4. "Analyse le sentiment de l'email sur [sujet]":
               → analyze_email_sentiment(query="sujet")
            
            📥 RECHERCHE ET RÉCUPÉRATION:
            5. "Cherche les emails de cette semaine":
               → get_recent_emails(days=7)
            
            6. "Montre-moi l'email de [personne]":
               → retrieve_email_content(query="personne")
            
            7. "Trouve les emails non lus":
               → get_unread_emails()
            
            ✍️ ACTIONS EMAIL:
            8. Après génération de réponse:
               → create_draft_email(recipient=..., subject=..., body=...)
            
            OUTILS DISPONIBLES:
            📊 ANALYSE: summarize_email, classify_email, analyze_email_sentiment (récupèrent l'email automatiquement)
            ✍️ GÉNÉRATION: generate_email_reply (récupère l'email automatiquement)
            📥 RÉCUPÉRATION: retrieve_email_content, search_emails, get_recent_emails, get_unread_emails
            📧 ACTIONS: create_draft_email, send_email, reply_to_email, forward_email, delete_draft
            ⚙️ GESTION: get_user_mailboxes, get_thread_statistics
            
            RÈGLES IMPORTANTES:
            ✅ Les fonctions summarize_email, classify_email, generate_email_reply, analyze_email_sentiment récupèrent automatiquement l'email
            ✅ Utilise retrieve_email_content SEULEMENT si l'utilisateur veut voir/lire le contenu d'un email
            ✅ Enchaîne les fonctions quand nécessaire (ex: generate_email_reply → create_draft_email)
            ✅ Pour les conversations générales sans action email, réponds normalement sans fonctions
            
            Analyse la demande et exécute les fonctions appropriées en séquence si nécessaire.
            """
            
            # Initialize context and results tracking for multi-step operations
            conversation_context = f"Demande de l'utilisateur: {user_message}"
            all_results = []
            max_iterations = 5
            
            # Multi-step conversation loop
            for iteration in range(1, max_iterations + 1):
                logger.info(f"🔄 Function calling iteration {iteration}/{max_iterations}")
                
                # Build messages for this iteration
                current_messages = [{"role": "system", "content": system_prompt}]
                
                # Add conversation history if available
                if conversation_history:
                    current_messages.extend(conversation_history)
                
                current_messages.append({"role": "user", "content": conversation_context})
                
                # Get available tools
                tools = self.tools_definition.get_email_tools()
                logger.debug(f"🔧 Available tools: {[tool['name'] for tool in tools]}")
                
                # Make request to Albert API
                response = self.api_client.make_request(current_messages, tools)
                choice = response.get('choices', [{}])[0]
                message = choice.get('message', {})
                
                # Check if the model wants to use tools
                tool_calls_made = False
                
                # Handle new tool_calls format
                if 'tool_calls' in message and message['tool_calls']:
                    tool_calls_made = True
                    logger.info(f"🛠️ Model wants to call {len(message['tool_calls'])} tool(s) in iteration {iteration}")
                    
                    # Execute all tool calls in this iteration
                    iteration_results = []
                    for j, tool_call in enumerate(message['tool_calls']):
                        if tool_call['type'] == 'function':
                            function_name = tool_call['function']['name']
                            raw_arguments = tool_call['function']['arguments']
                            
                            logger.info(f"🔧 Iteration {iteration}, Tool {j+1}: {function_name}")
                            
                            try:
                                function_args = json.loads(raw_arguments)
                                logger.info(f"✅ Successfully parsed arguments for {function_name}")
                            except json.JSONDecodeError as e:
                                logger.error(f"❌ Invalid JSON in function arguments for {function_name}: {e}")
                                continue
                            
                            # Execute the function
                            function_result = self.function_executor.execute_function(function_name, function_args, user_id)
                            
                            step_result = {
                                'iteration': iteration,
                                'step': len(all_results) + 1,
                                'function': function_name,
                                'args': function_args,
                                'result': function_result,
                                'success': function_result.get('success', False)
                            }
                            
                            iteration_results.append(step_result)
                            all_results.append(step_result)
                            
                            # Build context for next iteration
                            if function_result.get('success'):
                                result_summary = self._summarize_function_result(function_name, function_result)
                                conversation_context += f"\n\n✅ {function_name}: {result_summary}"
                            else:
                                error_msg = function_result.get('error', 'Erreur inconnue')
                                conversation_context += f"\n\n❌ {function_name}: Échec - {error_msg}"
                    
                    logger.info(f"📊 Completed iteration {iteration} with {len(iteration_results)} tool calls")
                
                # Handle legacy function_call format
                elif 'function_call' in message:
                    tool_calls_made = True
                    function_call = message['function_call']
                    function_name = function_call['name']
                    
                    logger.info(f"📞 Legacy function call in iteration {iteration}: {function_name}")
                    
                    try:
                        function_args = json.loads(function_call['arguments'])
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Invalid JSON in legacy function arguments: {e}")
                        break
                    
                    function_result = self.function_executor.execute_function(function_name, function_args, user_id)
                    
                    step_result = {
                        'iteration': iteration,
                        'step': len(all_results) + 1,
                        'function': function_name,
                        'args': function_args,
                        'result': function_result,
                        'success': function_result.get('success', False)
                    }
                    
                    all_results.append(step_result)
                    
                    if function_result.get('success'):
                        result_summary = self._summarize_function_result(function_name, function_result)
                        conversation_context += f"\n\n✅ {function_name}: {result_summary}"
                    else:
                        error_msg = function_result.get('error', 'Erreur inconnue')
                        conversation_context += f"\n\n❌ {function_name}: Échec - {error_msg}"
                
                # If no tools were called, we're done
                if not tool_calls_made:
                    logger.info(f"🏁 No more tools called in iteration {iteration}")
                    
                    # If we have results, format them as multi-step response
                    if all_results:
                        final_content = message.get('content', '').strip()
                        logger.info("🎨 Formatting final multi-step response")
                        return self._format_multi_step_response(all_results, user_message, final_content)
                    else:
                        # No function calls were made - regular conversational response
                        content = message.get('content', '').strip()
                        if content:
                            logger.info("💬 Generated conversational response")
                            return {
                                'success': True,
                                'response': content,
                                'type': 'conversation'
                            }
                        else:
                            return {
                                'success': True,
                                'response': 'Je suis désolé, je n\'ai pas pu traiter votre demande. Pouvez-vous la reformuler ?',
                                'type': 'conversation'
                            }
            
            # If we reached max iterations, format response with what we have
            if all_results:
                logger.warning(f"⚠️ Reached max iterations ({max_iterations})")
                return self._format_multi_step_response(all_results, user_message, "Traitement terminé après plusieurs étapes.")
            
            # Fallback response
            return {
                'success': True,
                'response': 'Je n\'ai pas pu identifier d\'action spécifique à effectuer. Comment puis-je vous aider ?',
                'type': 'conversation'
            }
            
        except Exception as e:
            logger.error(f"❌ Error in unified function calling: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'response': 'Une erreur s\'est produite lors du traitement. Comment puis-je vous aider autrement ?',
                'type': 'error'
            }
    
    def _summarize_function_result(self, function_name: str, function_result: Dict[str, Any]) -> str:
        """Create a concise summary of a function result for context building."""
        try:
            result_data = function_result.get('result', {})
            
            if function_name == 'retrieve_email_content':
                if result_data.get('success'):
                    metadata = result_data.get('metadata', {})
                    subject = metadata.get('subject', 'Sans sujet')
                    sender = metadata.get('sender_name', 'Expéditeur inconnu')
                    email_content = result_data.get('email_content', '')
                    
                    if email_content:
                        return f"Email récupéré: '{subject}' de {sender}. Contenu de l'email:\n\n{email_content}"
                    else:
                        return f"Email récupéré: '{subject}' de {sender} (contenu vide)"
                else:
                    return "Échec de récupération d'email"
            
            elif function_name == 'summarize_email':
                if result_data.get('success'):
                    return "Email résumé avec succès"
                else:
                    return "Échec du résumé"
            
            elif function_name == 'create_draft_email':
                if result_data.get('success'):
                    return "Brouillon créé avec succès"
                else:
                    return "Échec de création de brouillon"
            
            else:
                if function_result.get('success'):
                    return f"{function_name} exécuté avec succès"
                else:
                    return f"Échec de {function_name}"
                    
        except Exception as e:
            logger.error(f"Error summarizing function result: {e}")
            return f"{function_name} - résumé indisponible"
    
    def _format_multi_step_response(self, all_results: List[Dict], original_message: str, final_content: str = "") -> Dict[str, Any]:
        """Format the final response from the unified function calling handler."""
        try:
            if not all_results:
                return {
                    'success': False,
                    'response': 'Aucune action n\'a pu être effectuée.',
                    'type': 'function_call_error'
                }
            
            # Count successful and failed steps
            successful_steps = [r for r in all_results if r.get('success', False)]
            failed_steps = [r for r in all_results if not r.get('success', False)]
            
            total_steps = len(all_results)
            success_count = len(successful_steps)
            
            # Determine overall success
            overall_success = success_count > 0
            
            # For single successful step, use the response formatter
            if total_steps == 1 and successful_steps:
                single_result = successful_steps[0]
                function_name = single_result['function']
                function_result = single_result['result']
                
                # Use the response formatter for single function calls
                formatted_response = self.response_formatter.format_function_response(
                    function_name, function_result, original_message
                )
                
                if formatted_response.get('success'):
                    return formatted_response
            
            # Build comprehensive response for multi-step operations
            response_parts = []
            
            # Add header with step summary
            if total_steps == 1:
                response_parts.append(f"🔧 **Action effectuée:** {all_results[0]['function']}")
            else:
                response_parts.append(f"🔧 **Actions effectuées:** {total_steps} étape(s) - {success_count} réussie(s)")
            
            # Add step details
            response_parts.append("\n**Détail des étapes:**")
            for result in all_results:
                step_num = result['step']
                function_name = result['function']
                success = result.get('success', False)
                
                if success:
                    summary = self._summarize_function_result(function_name, result['result'])
                    response_parts.append(f"✅ **Étape {step_num}:** {summary}")
                else:
                    error_msg = result['result'].get('error', 'Erreur inconnue')
                    response_parts.append(f"❌ **Étape {step_num}:** {function_name} - {error_msg}")
            
            # Add detailed results for successful final steps
            if successful_steps:
                last_successful = successful_steps[-1]
                function_name = last_successful['function']
                function_result = last_successful['result']
                
                # Use the response formatter for detailed content
                formatted_response = self.response_formatter.format_function_response(
                    function_name, function_result, original_message
                )
                
                if formatted_response.get('success'):
                    response_parts.append(f"\n{formatted_response['response']}")
            
            # Add final content from the model if provided
            if final_content:
                response_parts.append(f"\n💬 **Analyse:**\n{final_content}")
            
            # Add error summary if there were failures
            if failed_steps:
                response_parts.append(f"\n⚠️ **Erreurs:** {len(failed_steps)} étape(s) ont échoué")
            
            response_text = "\n".join(response_parts)
            
            return {
                'success': overall_success,
                'response': response_text,
                'type': 'multi_step_completed' if total_steps > 1 else 'function_call',
                'steps_total': total_steps,
                'steps_successful': success_count,
                'steps_failed': len(failed_steps),
                'all_results': all_results,
                'final_function': successful_steps[-1]['function'] if successful_steps else None
            }
            
        except Exception as e:
            logger.error(f"Error formatting multi-step response: {e}", exc_info=True)
            return {
                'success': False,
                'response': f"Erreur lors du formatage de la réponse: {str(e)}",
                'type': 'function_call_error'
            }
