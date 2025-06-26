"""
Response formatter for chatbot function results.

This module handles formatting of function execution results into user-friendly responses.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Formats function execution results into user-friendly responses."""
    
    @staticmethod
    def format_function_response(function_name: str, function_result: Dict[str, Any], original_message: str) -> Dict[str, Any]:
        """
        Format the response based on the function that was called.
        
        Args:
            function_name: Name of the function that was executed
            function_result: Result from the function execution
            original_message: Original user message
            
        Returns:
            Formatted response dictionary
        """
        try:
            result_data = function_result.get('result', {})
            
            if function_name == 'summarize_email':
                return ResponseFormatter._format_summary_response(result_data)
            elif function_name == 'generate_email_reply':
                return ResponseFormatter._format_reply_response(result_data)
            elif function_name == 'classify_email':
                return ResponseFormatter._format_classification_response(result_data)
            elif function_name == 'search_emails':
                return ResponseFormatter._format_search_emails_response(result_data)
            elif function_name == 'get_recent_emails':
                return ResponseFormatter._format_recent_emails_response(result_data)
            elif function_name == 'retrieve_email_content':
                return ResponseFormatter._format_retrieve_content_response(result_data)
            elif function_name == 'create_draft_email':
                return ResponseFormatter._format_draft_response(result_data)
            else:
                return ResponseFormatter._format_generic_response(function_name, function_result)
                
        except Exception as e:
            logger.error(f"Error formatting function response: {e}")
            return {
                'success': False,
                'response': f"Erreur lors du formatage de la réponse pour {function_name}.",
                'type': 'error',
                'function_used': function_name
            }
    
    @staticmethod
    def _format_summary_response(result_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format email summary response."""
        if result_data.get('success'):
            summary_data = result_data.get('summary', {})
            if isinstance(summary_data, dict):
                summary_text = summary_data.get('summary', 'Résumé généré avec succès.')
                key_points = summary_data.get('key_points', [])
                urgency = summary_data.get('urgency_level', 'medium')
                
                response_text = f"📧 **Résumé de l'email:**\n\n{summary_text}"
                
                if key_points:
                    response_text += f"\n\n**Points clés:**\n"
                    for point in key_points[:3]:  # Limit to 3 key points
                        response_text += f"• {point}\n"
                
                response_text += f"\n**Niveau d'urgence:** {urgency}"
            else:
                response_text = f"📧 **Résumé de l'email:**\n\n{str(summary_data)}"
        else:
            response_text = "Je n'ai pas pu résumer cet email. Veuillez vérifier le contenu."
        
        return {
            'success': True,
            'response': response_text,
            'type': 'email_summary',
            'function_used': 'summarize_email'
        }
    
    @staticmethod
    def _format_reply_response(result_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format email reply response."""
        if result_data.get('success'):
            response_data = result_data.get('response', {})
            if isinstance(response_data, dict):
                reply_text = response_data.get('response', 'Réponse générée avec succès.')
                subject = response_data.get('subject', 'Re: Votre email')
                tone = response_data.get('tone_used', 'professional')
                
                response_text = f"✉️ **Réponse proposée:**\n\n**Sujet:** {subject}\n**Ton:** {tone}\n\n{reply_text}"
            else:
                response_text = f"✉️ **Réponse proposée:**\n\n{str(response_data)}"
        else:
            response_text = "Je n'ai pas pu générer une réponse à cet email."
        
        return {
            'success': True,
            'response': response_text,
            'type': 'email_reply',
            'function_used': 'generate_email_reply'
        }
    
    @staticmethod
    def _format_classification_response(result_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format email classification response."""
        if result_data.get('success'):
            classification = result_data.get('classification', {})
            if isinstance(classification, dict):
                category = classification.get('primary_category', 'Non classé')
                confidence = classification.get('confidence_score', 0.5)
                reasoning = classification.get('reasoning', 'Aucune explication disponible')
                response_text = f"🏷️ **Classification de l'email:**\n\n**Catégorie:** {category}\n**Confiance:** {confidence:.0%}\n**Explication:** {reasoning}"
            else:
                response_text = f"🏷️ **Classification de l'email:**\n\n{str(classification)}"
        else:
            response_text = "Je n'ai pas pu classifier cet email."
        
        return {
            'success': True,
            'response': response_text,
            'type': 'email_classification',
            'function_used': 'classify_email'
        }
    
    @staticmethod
    def _format_search_emails_response(result_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format email search response."""
        emails = result_data.get('emails', [])
        count = result_data.get('count', 0)
        
        if count > 0:
            response_text = f"🔍 **Résultats de recherche:** {count} email(s) trouvé(s)\n\n"
            for i, email in enumerate(emails[:5], 1):  # Show first 5 results
                subject = email.get('subject', 'Sans sujet')
                sender = email.get('sender_email', 'Expéditeur inconnu')
                response_text += f"{i}. **{subject}** (de {sender})\n"
        else:
            response_text = "🔍 Aucun email trouvé pour cette recherche."
        
        return {
            'success': True,
            'response': response_text,
            'type': 'email_search',
            'function_used': 'search_emails'
        }
    
    @staticmethod
    def _format_recent_emails_response(result_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format recent emails response."""
        emails = result_data.get('emails', [])
        count = result_data.get('count', 0)
        
        if count > 0:
            response_text = f"📬 **Emails récents:** {count} email(s) trouvé(s)\n\n"
            for i, email in enumerate(emails[:5], 1):
                subject = email.get('subject', 'Sans sujet')
                sender = email.get('sender_email', 'Expéditeur inconnu')
                date = email.get('date', 'Date inconnue')
                response_text += f"{i}. **{subject}** (de {sender}, {date})\n"
        else:
            response_text = "📬 Aucun email récent trouvé."
        
        return {
            'success': True,
            'response': response_text,
            'type': 'recent_emails',
            'function_used': 'get_recent_emails'
        }
    
    @staticmethod
    def _format_retrieve_content_response(result_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format email content retrieval response."""
        if result_data.get('success'):
            email_content = result_data.get('email_content', '')
            metadata = result_data.get('metadata', {})
            query = result_data.get('query', '')
            
            subject = metadata.get('subject', 'Sans sujet')
            sender_name = metadata.get('sender_name', 'Expéditeur inconnu')
            sender_email = metadata.get('sender_email', '')
            
            response_text = f"📧 **Email trouvé pour votre requête:** \"{query}\"\n\n"
            response_text += f"**Sujet:** {subject}\n"
            response_text += f"**De:** {sender_name}"
            if sender_email:
                response_text += f" <{sender_email}>"
            response_text += f"\n\n**Contenu de l'email récupéré avec succès.**\n\n"
            response_text += "Vous pouvez maintenant me demander de:\n"
            response_text += "• Résumer cet email\n"
            response_text += "• Générer une réponse à cet email\n"
            response_text += "• Classifier cet email\n"
            
            return {
                'success': True,
                'response': response_text,
                'type': 'email_content_retrieved',
                'function_used': 'retrieve_email_content',
                'email_data': {
                    'content': email_content,
                    'subject': subject,
                    'sender': f"{sender_name} <{sender_email}>" if sender_email else sender_name,
                    'metadata': metadata
                }
            }
        else:
            error_msg = result_data.get('error', 'Erreur inconnue')
            query = result_data.get('query', '')
            response_text = f"❌ **Impossible de récupérer l'email pour:** \"{query}\"\n\n{error_msg}"
            
            return {
                'success': False,
                'response': response_text,
                'type': 'email_content_retrieval_error',
                'function_used': 'retrieve_email_content'
            }
    
    @staticmethod
    def _format_draft_response(result_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format draft creation response."""
        if result_data.get('success'):
            subject = result_data.get('subject', 'Sans sujet')
            recipients_count = result_data.get('recipients_count', 0)
            message_id = result_data.get('message_id', '')
            
            response_text = f"📝 **Brouillon créé avec succès !**\n\n"
            response_text += f"**Sujet:** {subject}\n"
            response_text += f"**Destinataires:** {recipients_count} personne(s)\n"
            response_text += f"**ID du brouillon:** {message_id}\n\n"
            response_text += "Le brouillon a été sauvegardé. Vous pouvez maintenant :\n"
            response_text += "• L'envoyer avec `send_email` en utilisant l'ID du brouillon\n"
            response_text += "• Le modifier ou le supprimer"
        else:
            error_msg = result_data.get('error', 'Erreur inconnue')
            response_text = f"❌ **Erreur lors de la création du brouillon:**\n\n{error_msg}"
        
        return {
            'success': result_data.get('success', False),
            'response': response_text,
            'type': 'draft_created',
            'function_used': 'create_draft_email'
        }
    
    @staticmethod
    def _format_generic_response(function_name: str, function_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format generic function response."""
        return {
            'success': True,
            'response': f"Fonction {function_name} exécutée avec succès.",
            'type': 'function_result',
            'function_used': function_name
        }
