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
               → generate_email_reply(query="personne", create_draft=true)
               ✅ Crée automatiquement un brouillon si create_draft=true
            
            3b. "Génère une réponse à l'email de [personne]" (sans créer de brouillon):
               → generate_email_reply(query="personne", create_draft=false)
            
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
            8. "Crée un brouillon pour répondre à [personne]":
               → generate_email_reply(query="personne", create_draft=true)
            
            9. Création manuelle de brouillon:
               → create_draft_email(recipient=..., subject=..., body=...)
            
            OUTILS DISPONIBLES:
            📊 ANALYSE: summarize_email, classify_email, analyze_email_sentiment (récupèrent l'email automatiquement)
            ✍️ GÉNÉRATION: generate_email_reply (récupère l'email automatiquement, peut créer un brouillon avec create_draft=true)
            📥 RÉCUPÉRATION: retrieve_email_content, search_emails, get_recent_emails, get_unread_emails
            📧 ACTIONS: create_draft_email, send_email, reply_to_email, forward_email, delete_draft
            ⚙️ GESTION: get_user_mailboxes, get_thread_statistics
            
            RÈGLES IMPORTANTES:
            ✅ Les fonctions summarize_email, classify_email, generate_email_reply, analyze_email_sentiment récupèrent automatiquement l'email
            ✅ generate_email_reply avec create_draft=true crée automatiquement un brouillon (pas besoin de create_draft_email séparé)
            ✅ Utilise retrieve_email_content SEULEMENT si l'utilisateur veut voir/lire le contenu d'un email
            ✅ Pour créer un brouillon de réponse, utilise generate_email_reply(create_draft=true) au lieu de deux fonctions séparées
            ✅ Pour les conversations générales sans action email, réponds normalement sans fonctions
            
            🚫 RÈGLES ANTI-RÉPÉTITION:
            ❌ NE JAMAIS répéter la même fonction avec les mêmes paramètres
            ❌ Une fois qu'une fonction comme summarize_email, classify_email, ou generate_email_reply a réussi, NE PAS la rappeler
            ❌ Si une fonction a déjà été exécutée avec succès, passer à l'étape suivante ou terminer
            ✅ Vérifier les résultats précédents avant d'appeler une nouvelle fonction
            
            Analyse la demande et exécute les fonctions appropriées en séquence si nécessaire, SANS RÉPÉTITION.
            """
            
            # Initialize context and results tracking for multi-step operations
            conversation_context = f"Demande de l'utilisateur: {user_message}"
            all_results = []
            max_iterations = 3  # Reduced to prevent excessive iterations
            completed_functions = set()  # Track completed functions to avoid repetition
            
            # Multi-step conversation loop
            for iteration in range(1, max_iterations + 1):
                logger.info(f"🔄 Function calling iteration {iteration}/{max_iterations}")
                
                # Build messages for this iteration
                current_messages = [{"role": "system", "content": system_prompt}]
                
                # Add conversation history if available
                if conversation_history:
                    current_messages.extend(conversation_history)
                
                # Add context about completed functions to prevent repetition
                if completed_functions:
                    context_with_completed = conversation_context + f"\n\nFONCTIONS DÉJÀ EXÉCUTÉES: {', '.join(completed_functions)}. Ne pas répéter ces fonctions sauf si nécessaire pour une étape différente."
                    current_messages.append({"role": "user", "content": context_with_completed})
                else:
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
                            
                            # Check if this function was already completed successfully
                            if function_name in completed_functions:
                                logger.warning(f"⚠️ Function {function_name} already completed, skipping to prevent repetition")
                                continue
                            
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
                                # Mark function as completed to prevent repetition
                                completed_functions.add(function_name)
                                
                                result_summary = self._summarize_function_result(function_name, function_result)
                                conversation_context += f"\n\n✅ {function_name}: {result_summary}"
                                
                                # For certain functions, mark the task as complete
                                if function_name in ['summarize_email', 'classify_email', 'generate_email_reply', 'analyze_email_sentiment']:
                                    conversation_context += f"\n\nTÂCHE TERMINÉE: {function_name} a été exécuté avec succès. Ne pas répéter cette fonction."
                                
                            else:
                                error_msg = function_result.get('error', 'Erreur inconnue')
                                conversation_context += f"\n\n❌ {function_name}: Échec - {error_msg}"
                    
                    logger.info(f"📊 Completed iteration {iteration} with {len(iteration_results)} tool calls")
                    
                    # If no new functions were executed (all were already completed), stop the loop
                    if not iteration_results:
                        logger.info("🛑 All requested functions already completed, stopping iteration")
                        break
                
                # Handle legacy function_call format
                elif 'function_call' in message:
                    tool_calls_made = True
                    function_call = message['function_call']
                    function_name = function_call['name']
                    
                    logger.info(f"📞 Legacy function call in iteration {iteration}: {function_name}")
                    
                    # Check if this function was already completed successfully
                    if function_name in completed_functions:
                        logger.warning(f"⚠️ Function {function_name} already completed, stopping to prevent repetition")
                        break
                    
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
                        # Mark function as completed to prevent repetition
                        completed_functions.add(function_name)
                        
                        result_summary = self._summarize_function_result(function_name, function_result)
                        conversation_context += f"\n\n✅ {function_name}: {result_summary}"
                        
                        # For certain functions, mark the task as complete
                        if function_name in ['summarize_email', 'classify_email', 'generate_email_reply', 'analyze_email_sentiment']:
                            conversation_context += f"\n\nTÂCHE TERMINÉE: {function_name} a été exécuté avec succès. Ne pas répéter cette fonction."
                            
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
        """Format the final response from the unified function calling handler with standardized style."""
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
            
            # For single successful step, use the response formatter directly
            if total_steps == 1 and successful_steps:
                single_result = successful_steps[0]
                function_name = single_result['function']
                function_result = single_result['result']
                
                # Use the response formatter for single function calls
                formatted_response = self.response_formatter.format_function_response(
                    function_name, function_result, original_message
                )
                
                if formatted_response.get('success'):
                    # Enhance the single function response with better formatting
                    enhanced_response = self._enhance_response_formatting(formatted_response['response'])
                    return {
                        **formatted_response,
                        'response': enhanced_response
                    }
            
            # Build comprehensive response for multi-step operations with standardized formatting
            response_parts = []
            
            # Add clean header
            if total_steps == 1:
                response_parts.append(f"## ✅ Action Terminée\n")
                response_parts.append(f"**Fonction exécutée :** `{all_results[0]['function']}`\n")
            else:
                response_parts.append(f"## 🔄 Traitement Multi-Étapes\n")
                response_parts.append(f"**Résumé :** {success_count}/{total_steps} étapes réussies\n")
            
            # Add step details with better formatting
            if total_steps > 1:
                response_parts.append("### 📋 Détail des Étapes\n")
                for i, result in enumerate(all_results, 1):
                    function_name = result['function']
                    success = result.get('success', False)
                    
                    if success:
                        status_icon = "✅"
                        status_text = "Réussie"
                    else:
                        status_icon = "❌"
                        status_text = "Échec"
                        error_msg = result['result'].get('error', 'Erreur inconnue')
                    
                    response_parts.append(f"{status_icon} **Étape {i}** : `{function_name}` - {status_text}")
                    
                    if not success and 'error_msg' in locals():
                        response_parts.append(f"   *Erreur : {error_msg}*")
                    
                    response_parts.append("")  # Add spacing
            
            # Add main result content from the most relevant successful function
            if successful_steps:
                last_successful = successful_steps[-1]
                function_name = last_successful['function']
                function_result = last_successful['result']
                
                # Use the response formatter for detailed content
                formatted_response = self.response_formatter.format_function_response(
                    function_name, function_result, original_message
                )
                
                if formatted_response.get('success'):
                    # Extract and enhance the main content
                    main_content = formatted_response['response']
                    enhanced_content = self._enhance_response_formatting(main_content)
                    
                    response_parts.append("---\n")  # Separator
                    response_parts.append(enhanced_content)
            
            # Add final analysis if provided
            if final_content and final_content.strip():
                response_parts.append("\n---\n")
                response_parts.append("### 📝 Analyse\n")
                response_parts.append(f"{final_content.strip()}\n")
            
            # Add error summary if there were failures
            if failed_steps:
                response_parts.append("\n---\n")
                response_parts.append(f"### ⚠️ Avertissements\n")
                response_parts.append(f"**{len(failed_steps)} étape(s) ont échoué** - Consultez les détails ci-dessus.\n")
            
            # Join all parts with proper spacing
            response_text = "\n".join(response_parts).strip()
            
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
                'response': f"## ❌ Erreur de Traitement\n\n**Détail :** {str(e)}\n\nVeuillez réessayer ou reformuler votre demande.",
                'type': 'function_call_error'
            }
    
    def _enhance_response_formatting(self, response_text: str) -> str:
        """
        Enhance and standardize the formatting of response text for better markdown parsing.
        
        Args:
            response_text: The raw response text to enhance
            
        Returns:
            Enhanced and properly formatted response text
        """
        try:
            if not response_text or not response_text.strip():
                return response_text
            
            # Clean up the input text
            lines = response_text.strip().split('\n')
            enhanced_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    enhanced_lines.append('')
                    continue
                
                # Standardize headers
                if line.startswith('**') and line.endswith(':**'):
                    # Convert **Header:** to proper markdown header
                    header_text = line.replace('**', '').replace(':', '').strip()
                    enhanced_lines.append(f"### {header_text}\n")
                elif line.startswith('**') and line.endswith('**') and ':' not in line:
                    # Convert **Bold Text** to proper bold
                    enhanced_lines.append(line)
                
                # Standardize email content formatting
                elif line.startswith('📧') or line.startswith('✉️'):
                    enhanced_lines.append(f"### {line}\n")
                
                # Standardize list items and status indicators
                elif line.startswith('✅') or line.startswith('❌') or line.startswith('⚠️'):
                    # Ensure proper spacing for status items
                    enhanced_lines.append(f"{line}")
                
                # Enhance code blocks and inline code
                elif 'Sujet:' in line or 'Ton:' in line or 'Destinataire:' in line:
                    # Format email metadata properly with design system approach
                    if ':' in line:
                        key, value = line.split(':', 1)
                        enhanced_lines.append(f"**{key.strip()}:** `{value.strip()}`")
                    else:
                        enhanced_lines.append(line)
                
                # Handle email body content with design system styling
                elif line.startswith('Bonjour') or line.startswith('Monsieur') or line.startswith('Madame'):
                    # Start of email content - add proper formatting
                    enhanced_lines.append("\n```email")
                    enhanced_lines.append(line)
                elif line.startswith('Cordialement') or line.startswith('Bien à vous') or line.startswith('Salutations'):
                    # End of email content
                    enhanced_lines.append(line)
                    enhanced_lines.append("```\n")
                
                # Handle function names and technical terms with consistent styling
                elif any(func in line for func in ['summarize_email', 'classify_email', 'generate_email_reply', 'retrieve_email_content']):
                    # Wrap function names in code formatting for technical clarity
                    for func in ['summarize_email', 'classify_email', 'generate_email_reply', 'retrieve_email_content', 'create_draft_email']:
                        if func in line:
                            line = line.replace(func, f"`{func}`")
                    enhanced_lines.append(line)
                
                else:
                    enhanced_lines.append(line)
            
            # Join lines and clean up excessive spacing
            enhanced_text = '\n'.join(enhanced_lines)
            
            # Clean up multiple consecutive newlines
            while '\n\n\n' in enhanced_text:
                enhanced_text = enhanced_text.replace('\n\n\n', '\n\n')
            
            # Ensure proper spacing around headers
            enhanced_text = enhanced_text.replace('\n###', '\n\n###')
            enhanced_text = enhanced_text.replace('###\n', '###\n\n')
            
            # Ensure proper spacing around code blocks
            enhanced_text = enhanced_text.replace('\n```', '\n\n```')
            enhanced_text = enhanced_text.replace('```\n', '```\n\n')
            
            # Final cleanup
            enhanced_text = enhanced_text.strip()
            
            return enhanced_text
            
        except Exception as e:
            logger.error(f"Error enhancing response formatting: {e}")
            return response_text  # Return original if enhancement fails
