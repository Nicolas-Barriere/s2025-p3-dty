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
            
            # Try multi-step function calling first
            multi_step_result = self._handle_multi_step_functions(user_message, user_id, conversation_history)
            if multi_step_result is not None:
                return multi_step_result
            
            # Fallback to single function call
            return self._handle_single_function_call(user_message, user_id, conversation_history)
            
        except Exception as e:
            logger.error(f"Error processing user message: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': 'Une erreur s\'est produite lors du traitement de votre message. Comment puis-je vous aider autrement ?',
                'type': 'error'
            }
    
    def _handle_single_function_call(self, user_message: str, user_id: str = None, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Handle single function call processing."""
        # System prompt for the AI assistant
        system_prompt = """
        Tu es un assistant intelligent spécialisé dans la gestion d'emails avec des capacités de fonction calling.
        
        Tu peux utiliser les outils suivants pour aider les utilisateurs:
        - summarize_email: Résumer un email
        - generate_email_reply: Générer une réponse à un email
        - classify_email: Classifier un email
        - search_emails: Rechercher des emails
        - get_recent_emails: Récupérer les emails récents
        - retrieve_email_content: Récupérer le contenu d'un email
        - create_draft_email: Créer un brouillon d'email
        
        Pour les conversations générales sans action email, réponds normalement sans utiliser de fonctions.
        """
        
        # Build messages for the conversation
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})
        
        # Get available tools
        tools = self.tools_definition.get_email_tools()
        logger.info(f"Available tools: {len(tools)} tools loaded")
        
        # Make request to Albert API with function calling
        response = self.api_client.make_request(messages, tools)
        
        # Process the response
        choice = response.get('choices', [{}])[0]
        message = choice.get('message', {})
        
        # Check if AI wants to call a function
        if 'tool_calls' in message and message['tool_calls']:
            tool_call = message['tool_calls'][0]  # Take the first tool call
            
            if tool_call['type'] == 'function':
                function_call = tool_call['function']
                function_name = function_call['name']
                
                logger.info(f"AI wants to call function: {function_name}")
                
                try:
                    function_args = json.loads(function_call['arguments'])
                    logger.info(f"✅ Successfully parsed function arguments for {function_name}")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Failed to parse function arguments: {e}")
                    return {
                        'success': False,
                        'response': "Erreur lors de l'analyse des paramètres de la fonction.",
                        'type': 'error'
                    }
                
                # Execute the function
                function_result = self.function_executor.execute_function(function_name, function_args, user_id)
                
                if function_result.get('success'):
                    # Format the response based on the function used
                    return self.response_formatter.format_function_response(function_name, function_result, user_message)
                else:
                    return {
                        'success': False,
                        'response': f"Erreur lors de l'exécution de {function_name}: {function_result.get('error', 'Erreur inconnue')}",
                        'type': 'error',
                        'function_used': function_name
                    }
        
        # Check for legacy function_call format
        elif 'function_call' in message:
            function_call = message['function_call']
            function_name = function_call['name']
            try:
                function_args = json.loads(function_call['arguments'])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse function arguments: {e}")
                return {
                    'success': False,
                    'response': "Erreur lors de l'analyse des paramètres de la fonction.",
                    'type': 'error'
                }
            
            logger.info(f"AI wants to call function (legacy): {function_name}")
            
            # Execute the function
            function_result = self.function_executor.execute_function(function_name, function_args, user_id)
            
            if function_result.get('success'):
                return self.response_formatter.format_function_response(function_name, function_result, user_message)
            else:
                return {
                    'success': False,
                    'response': f"Erreur lors de l'exécution de {function_name}: {function_result.get('error', 'Erreur inconnue')}",
                    'type': 'error',
                    'function_used': function_name
                }
        
        # No function call - regular conversational response
        content = message.get('content', '').strip()
        if content:
            logger.info("Generated conversational response")
            return {
                'success': True,
                'response': content,
                'type': 'conversation'
            }
        
        # Fallback response
        return {
            'success': True,
            'response': 'Je suis désolé, je n\'ai pas pu traiter votre demande. Pouvez-vous la reformuler ?',
            'type': 'conversation'
        }
    
    def _handle_multi_step_functions(self, user_message: str, user_id: str = None, conversation_history: List[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """
        Handle multi-step function calling for complex requests.
        
        Args:
            user_message: The user's input message
            user_id: User ID for email operations
            conversation_history: Previous conversation messages
            
        Returns:
            Dictionary containing the final response after function calls, or None if not applicable
        """
        try:
            logger.info("Starting multi-step function calling")
            
            # Dynamic system prompt for intelligent function chaining
            dynamic_prompt = """
            Tu es un assistant intelligent avec accès à des outils de gestion d'emails. 
            Tu peux analyser la demande de l'utilisateur et décider quels outils utiliser, 
            dans quel ordre, et combien d'étapes sont nécessaires.

            🎯 APPROCHE DYNAMIQUE:
            - Analyse la demande de l'utilisateur
            - Décide quels outils utiliser et dans quel ordre
            - Tu peux faire plusieurs appels d'outils en séquence
            - Utilise les résultats d'un outil comme entrée pour le suivant si nécessaire
            - Sois créatif et flexible dans ton approche

            🔧 OUTILS DISPONIBLES:
            - retrieve_email_content: Récupère le contenu complet d'un email spécifique
            - search_emails: Recherche des emails par mots-clés
            - get_recent_emails: Récupère les emails récents
            - summarize_email: Résume un email (PEUT récupérer automatiquement l'email avec retrieve_email=true)
            - classify_email: Classifie un email (PEUT récupérer automatiquement l'email avec retrieve_email=true)
            - generate_email_reply: Génère une réponse à un email (PEUT récupérer automatiquement l'email avec retrieve_email=true)
            - create_draft_email: Crée un brouillon d'email

            ✨ RÈGLES IMPORTANTES:
            - Les fonctions summarize_email, classify_email et generate_email_reply peuvent récupérer automatiquement les emails
            - Utilise retrieve_email=true quand l'utilisateur mentionne un email spécifique
            - Si une demande semble nécessiter des outils, utilise-les
            - Si c'est une conversation générale, réponds normalement

            Analyse la demande et agis en conséquence.
            """
            
            # Initialize conversation history
            if conversation_history is None:
                conversation_history = []
            
            # Build the conversation
            messages = [{"role": "system", "content": dynamic_prompt}]
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_message})
            
            # Get available tools
            tools = self.tools_definition.get_email_tools()
            
            # Start the function calling loop
            max_iterations = 5  # Prevent infinite loops
            iteration = 0
            all_results = []
            conversation_context = ""
            
            while iteration < max_iterations:
                iteration += 1
                logger.info(f"🔄 Multi-step iteration {iteration}/{max_iterations}")
                
                # Add accumulated context to the conversation if we have previous results
                current_messages = messages.copy()
                if conversation_context:
                    current_messages.append({
                        "role": "assistant", 
                        "content": f"Contexte des outils précédents:\n{conversation_context}"
                    })
                    current_messages.append({
                        "role": "user", 
                        "content": "Continue avec les outils suivants si nécessaire, ou fournis la réponse finale."
                    })
                
                # Make request to get the model's decision
                response = self.api_client.make_request(current_messages, tools)
                choice = response.get('choices', [{}])[0]
                message = choice.get('message', {})
                
                # Check if the model wants to use tools
                tool_calls_made = False
                
                if 'tool_calls' in message and message['tool_calls']:
                    tool_calls_made = True
                    logger.info(f"Model wants to call {len(message['tool_calls'])} tool(s) in iteration {iteration}")
                    
                    # Execute all tool calls in this iteration
                    for j, tool_call in enumerate(message['tool_calls']):
                        if tool_call['type'] == 'function':
                            function_name = tool_call['function']['name']
                            raw_arguments = tool_call['function']['arguments']
                            
                            try:
                                function_args = json.loads(raw_arguments)
                                logger.info(f"Iteration {iteration}, Tool {j+1}: Executing {function_name}")
                            except json.JSONDecodeError as e:
                                logger.error(f"Invalid JSON in function arguments for {function_name}: {e}")
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
                            
                            all_results.append(step_result)
                            
                            # Build context for next iteration
                            if function_result.get('success'):
                                result_summary = self._summarize_function_result(function_name, function_result)
                                conversation_context += f"\n\n✅ {function_name}: {result_summary}"
                            else:
                                error_msg = function_result.get('error', 'Erreur inconnue')
                                conversation_context += f"\n\n❌ {function_name}: Échec - {error_msg}"
                
                # If no tools were called, the model is done
                if not tool_calls_made:
                    logger.info(f"🏁 No more tools called in iteration {iteration}. Multi-step complete.")
                    
                    # Check if we have any results to format
                    if all_results:
                        final_content = message.get('content', '').strip()
                        return self._format_multi_step_response(all_results, user_message, final_content)
                    else:
                        # No tools were used, this wasn't a function calling request
                        return None
            
            # If we reached max iterations, format response with what we have
            if all_results:
                logger.warning(f"Multi-step reached max iterations ({max_iterations})")
                return self._format_multi_step_response(all_results, user_message, "Traitement terminé après plusieurs étapes.")
            
            # No function calls were made
            return None
            
        except Exception as e:
            logger.error(f"Error in multi-step function calling: {e}", exc_info=True)
            return None
    
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
        """Format the final response from multi-step processing."""
        try:
            if not all_results:
                return {
                    'success': False,
                    'response': 'Aucune action n\'a pu être effectuée.',
                    'type': 'multi_step_error'
                }
            
            # Count successful and failed steps
            successful_steps = [r for r in all_results if r.get('success', False)]
            failed_steps = [r for r in all_results if not r.get('success', False)]
            
            total_steps = len(all_results)
            success_count = len(successful_steps)
            
            # Determine overall success
            overall_success = success_count > 0
            
            # Build comprehensive response
            response_parts = []
            
            # Add header with step summary
            if total_steps == 1:
                response_parts.append(f"🔧 **Action effectuée:** {all_results[0]['function']}")
            else:
                response_parts.append(f"🔧 **Actions effectuées:** {total_steps} étape(s) - {success_count} réussie(s)")
            
            # Add detailed results for successful final steps
            if successful_steps:
                last_successful = successful_steps[-1]
                function_name = last_successful['function']
                function_result = last_successful['result']
                
                # Use the response formatter for the final result
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
                'type': 'multi_step_completed',
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
                'type': 'multi_step_error'
            }
