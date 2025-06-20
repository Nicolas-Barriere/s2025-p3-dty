"""
Chatbot implementation using Albert API for mail processing operations.

This module provides functionality for:
- Mail summarization
- Mail answer generation
- Mail classification

Author: ANCT
Date: 2025-06-19
"""

import json
import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


class MailClassification(Enum):
    """Mail classification categories."""
    URGENT = "urgent"
    NORMAL = "normal"
    LOW_PRIORITY = "low_priority"
    SPAM = "spam"
    INFORMATION = "information"
    REQUEST = "request"
    COMPLAINT = "complaint"
    SUPPORT = "support"


@dataclass
class AlbertConfig:
    """Configuration for Albert API."""
    name: str = "albert-etalab"
    base_url: str = "https://albert.api.etalab.gouv.fr/v1"
    api_key: str = "sk-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo0NTQsInRva2VuX2lkIjoxNjM5LCJleHBpcmVzX2F0IjoxNzgxNzMzNjAwfQ.CwVlU_n4uj6zsfxZV1AFLxfwqzd7puYzs4Agp8HhYxs"
    model: str = "albert-large"


class AlbertChatbot:
    """
    Chatbot implementation using Albert API for mail processing operations.
    
    Provides functionality for mail summarization, answer generation, and classification
    using Albert's language model with function calling capabilities.
    """

    def __init__(self, config: Optional[AlbertConfig] = None):
        """
        Initialize the Albert chatbot.
        
        Args:
            config: Configuration for Albert API. If None, uses default config.
        """
        self.config = config or AlbertConfig()
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json',
        })

    def _make_request(self, messages: List[Dict[str, str]], functions: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Make a request to Albert API.
        
        Args:
            messages: List of message objects for the conversation
            functions: Optional list of function definitions for function calling
            
        Returns:
            Response from Albert API
            
        Raises:
            requests.RequestException: If API request fails
        """
        try:
            payload = {
                "model": self.config.model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 1000,
            }
            
            if functions:
                payload["functions"] = functions
                payload["function_call"] = "auto"
            
            logger.info(f"Making request to Albert API with {len(messages)} messages")
            
            response = self.session.post(
                f"{self.config.base_url}/chat/completions",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info("Successfully received response from Albert API")
            return result
            
        except requests.RequestException as e:
            logger.error(f"Failed to make request to Albert API: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response from Albert API: {e}")
            raise

    def summarize_mail(self, mail_content: str, sender: str = "", subject: str = "") -> Dict[str, Any]:
        """
        Summarize an email content using Albert API.
        
        Args:
            mail_content: The content of the email to summarize
            sender: Email sender (optional)
            subject: Email subject (optional)
            
        Returns:
            Dictionary containing the summary and metadata
        """
        try:
            logger.info(f"Summarizing mail from sender: {sender}")
            
            # Prepare the mail context
            mail_context = f"""
            Expéditeur: {sender}
            Sujet: {subject}
            Contenu: {mail_content}
            """
            
            functions = [{
                "name": "summarize_email",
                "description": "Résume le contenu d'un email en français",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Résumé concis de l'email en français"
                        },
                        "key_points": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Points clés de l'email"
                        },
                        "action_required": {
                            "type": "boolean",
                            "description": "Indique si une action est requise"
                        },
                        "urgency_level": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": "Niveau d'urgence"
                        }
                    },
                    "required": ["summary", "key_points", "action_required", "urgency_level"]
                }
            }]
            
            messages = [
                {
                    "role": "system",
                    "content": "Tu es un assistant IA spécialisé dans l'analyse et le résumé d'emails. "
                              "Tu dois analyser le contenu des emails et fournir des résumés clairs et concis en français."
                },
                {
                    "role": "user",
                    "content": f"Analyse et résume cet email:\n\n{mail_context}"
                }
            ]
            
            response = self._make_request(messages, functions)
            
            # Extract function call result or content response
            choice = response.get('choices', [{}])[0]
            message = choice.get('message', {})
            
            if 'function_call' in message:
                function_call = message['function_call']
                if function_call['name'] == 'summarize_email':
                    summary_data = json.loads(function_call['arguments'])
                    logger.info("Successfully summarized email using function call")
                    return {
                        'success': True,
                        'summary': summary_data,
                        'original_sender': sender,
                        'original_subject': subject
                    }
            
            # Albert API uses content-based responses (which are excellent)
            content = message.get('content', '').strip()
            if content:
                logger.info("Successfully summarized email using content response")
                # Parse the content to extract structured information when possible
                summary_data = self._parse_summary_content(content)
                return {
                    'success': True,
                    'summary': summary_data,
                    'original_sender': sender,
                    'original_subject': subject
                }
            
            # Only fail if no content at all
            logger.error("No content received from Albert API")
            return {
                'success': False,
                'error': 'Aucune réponse reçue de l\'API Albert',
                'summary': {'summary': 'Erreur lors du résumé de l\'email.'},
                'original_sender': sender,
                'original_subject': subject
            }
            
        except Exception as e:
            logger.error(f"Error summarizing mail: {e}")
            return {
                'success': False,
                'error': str(e),
                'summary': {'summary': 'Erreur lors du résumé de l\'email.'}
            }

    def generate_mail_answer(
        self, 
        original_mail: str, 
        context: str = "",
        tone: str = "professional",
        language: str = "french"
    ) -> Dict[str, Any]:
        """
        Generate an answer to an email using Albert API.
        
        Args:
            original_mail: The original email content to respond to
            context: Additional context for the response
            tone: Tone of the response (professional, friendly, formal)
            language: Language for the response
            
        Returns:
            Dictionary containing the generated response and metadata
        """
        try:
            logger.info(f"Generating mail answer with tone: {tone}")
            
            functions = [{
                "name": "generate_email_response",
                "description": "Génère une réponse professionnelle à un email",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "response": {
                            "type": "string",
                            "description": "Réponse complète à l'email"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Sujet proposé pour la réponse"
                        },
                        "tone_used": {
                            "type": "string",
                            "description": "Ton utilisé dans la réponse"
                        },
                        "estimated_reading_time": {
                            "type": "integer",
                            "description": "Temps de lecture estimé en secondes"
                        }
                    },
                    "required": ["response", "subject", "tone_used"]
                }
            }]
            
            system_prompt = f"""
            Tu es un assistant de rédaction d'emails professionnel. 
            Tu dois générer des réponses appropriées aux emails en {language} avec un ton {tone}.
            Assure-toi que tes réponses sont:
            - Claires et concises
            - Respectueuses et professionnelles
            - Adaptées au contexte
            - Bien structurées
            """
            
            user_prompt = f"""
            Génère une réponse à cet email:
            
            Email original:
            {original_mail}
            
            Contexte supplémentaire:
            {context}
            
            Ton souhaité: {tone}
            Langue: {language}
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self._make_request(messages, functions)
            
            # Extract function call result or content response
            choice = response.get('choices', [{}])[0]
            message = choice.get('message', {})
            
            if 'function_call' in message:
                function_call = message['function_call']
                if function_call['name'] == 'generate_email_response':
                    response_data = json.loads(function_call['arguments'])
                    logger.info("Successfully generated email response using function call")
                    return {
                        'success': True,
                        'response': response_data,
                        'context_used': context,
                        'tone_requested': tone
                    }
            
            # Albert API uses content-based responses
            content = message.get('content', '').strip()
            if content:
                logger.info("Successfully generated email response using content response")
                # Parse content to structure the response
                response_data = self._parse_answer_content(content, tone)
                return {
                    'success': True,
                    'response': response_data,
                    'context_used': context,
                    'tone_requested': tone
                }
            
            # Only fail if no content at all
            logger.error("No content received from Albert API for answer generation")
            return {
                'success': False,
                'error': 'Aucune réponse reçue de l\'API Albert',
                'response': {
                    'response': 'Erreur lors de la génération de la réponse.',
                    'subject': 'Réponse',
                    'tone_used': tone
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating mail answer: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': {'response': 'Erreur lors de la génération de la réponse.'}
            }

    def classify_mail(
        self, 
        mail_content: str, 
        sender: str = "", 
        subject: str = "",
        custom_categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Classify an email into categories using Albert API.
        
        Args:
            mail_content: The content of the email to classify
            sender: Email sender (optional)
            subject: Email subject (optional)
            custom_categories: Custom classification categories (optional)
            
        Returns:
            Dictionary containing the classification results
        """
        try:
            logger.info(f"Classifying mail from sender: {sender}")
            
            # Use custom categories or default ones
            categories = custom_categories or [cat.value for cat in MailClassification]
            
            mail_context = f"""
            Expéditeur: {sender}
            Sujet: {subject}
            Contenu: {mail_content}
            """
            
            functions = [{
                "name": "classify_email",
                "description": "Classifie un email selon différentes catégories",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "primary_category": {
                            "type": "string",
                            "enum": categories,
                            "description": "Catégorie principale de l'email"
                        },
                        "secondary_categories": {
                            "type": "array",
                            "items": {"type": "string", "enum": categories},
                            "description": "Catégories secondaires applicables"
                        },
                        "confidence_score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Score de confiance de la classification"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Justification de la classification"
                        },
                        "requires_human_review": {
                            "type": "boolean",
                            "description": "Indique si une révision humaine est recommandée"
                        }
                    },
                    "required": ["primary_category", "confidence_score", "reasoning"]
                }
            }]
            
            system_prompt = f"""
            Tu es un système de classification d'emails expert. 
            Tu dois analyser le contenu, l'expéditeur et le sujet des emails pour les classer 
            dans les catégories suivantes: {', '.join(categories)}.
            
            Fournis toujours une justification claire de tes classifications.
            """
            
            user_prompt = f"""
            Classifie cet email selon les catégories disponibles:
            
            {mail_context}
            
            Catégories disponibles: {', '.join(categories)}
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self._make_request(messages, functions)
            
            # Extract function call result or content response
            choice = response.get('choices', [{}])[0]
            message = choice.get('message', {})
            
            if 'function_call' in message:
                function_call = message['function_call']
                if function_call['name'] == 'classify_email':
                    classification_data = json.loads(function_call['arguments'])
                    logger.info(f"Successfully classified email as: {classification_data.get('primary_category')}")
                    return {
                        'success': True,
                        'classification': classification_data,
                        'available_categories': categories,
                        'original_sender': sender,
                        'original_subject': subject
                    }
            
            # Albert API uses content-based responses
            content = message.get('content', '').strip()
            if content:
                logger.info("Successfully classified email using content response")
                # Parse content to extract classification information
                classification_data = self._parse_classification_content(content, categories)
                return {
                    'success': True,
                    'classification': classification_data,
                    'available_categories': categories,
                    'original_sender': sender,
                    'original_subject': subject
                }
            
            # Only fail if no content at all
            logger.error("No content received from Albert API for classification")
            return {
                'success': False,
                'error': 'Aucune réponse reçue de l\'API Albert',
                'classification': {
                    'primary_category': 'normal',
                    'confidence_score': 0.0,
                    'reasoning': 'Erreur - aucune réponse de l\'API.'
                },
                'available_categories': categories,
                'original_sender': sender,
                'original_subject': subject
            }
            
        except Exception as e:
            logger.error(f"Error classifying mail: {e}")
            return {
                'success': False,
                'error': str(e),
                'classification': {
                    'primary_category': 'normal',
                    'confidence_score': 0.0,
                    'reasoning': f'Erreur lors de la classification: {str(e)}'
                }
            }

    def process_mail_batch(self, mails: List[Dict[str, str]], operation: str = "summarize") -> List[Dict[str, Any]]:
        """
        Process multiple mails in batch.
        
        Args:
            mails: List of mail dictionaries with 'content', 'sender', 'subject' keys
            operation: Operation to perform ('summarize', 'classify', or 'answer')
            
        Returns:
            List of processed results
        """
        results = []
        
        logger.info(f"Processing batch of {len(mails)} mails for operation: {operation}")
        
        for i, mail in enumerate(mails):
            try:
                mail_content = mail.get('content', '')
                sender = mail.get('sender', '')
                subject = mail.get('subject', '')
                
                if operation == "summarize":
                    result = self.summarize_mail(mail_content, sender, subject)
                elif operation == "classify":
                    result = self.classify_mail(mail_content, sender, subject)
                elif operation == "answer":
                    context = mail.get('context', '')
                    tone = mail.get('tone', 'professional')
                    result = self.generate_mail_answer(mail_content, context, tone)
                else:
                    result = {'success': False, 'error': f'Unknown operation: {operation}'}
                
                result['batch_index'] = i
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error processing mail {i} in batch: {e}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'batch_index': i
                })
        
        logger.info(f"Completed batch processing: {len(results)} results")
        return results

    def detect_intent(self, user_message: str) -> Dict[str, Any]:
        """
        Detect user intent from their message using keyword analysis and AI assistance.
        
        Args:
            user_message: The user's input message
            
        Returns:
            Dictionary containing intent information
        """
        try:
            logger.info("Detecting user intent")
            
            # Simple keyword-based detection first
            message_lower = user_message.lower()
            
            # High confidence keyword detection
            if any(keyword in message_lower for keyword in ['résume', 'résumé', 'synthèse', 'analyse cet email', 'que dit cet email']):
                return {
                    'success': True,
                    'intent': 'summarize_email',
                    'confidence': 0.9,
                    'extracted_content': user_message,
                    'reasoning': 'Mots-clés de résumé détectés'
                }
            
            if any(keyword in message_lower for keyword in ['réponds', 'réponse', 'écris une réponse', 'réponds à cet email', 'génère une réponse']):
                return {
                    'success': True,
                    'intent': 'generate_reply',
                    'confidence': 0.9,
                    'extracted_content': user_message,
                    'reasoning': 'Mots-clés de réponse détectés'
                }
            
            if any(keyword in message_lower for keyword in ['classe', 'catégorise', 'quel type', 'priorité', 'classifie']):
                return {
                    'success': True,
                    'intent': 'classify_email',
                    'confidence': 0.9,
                    'extracted_content': user_message,
                    'reasoning': 'Mots-clés de classification détectés'
                }
            
            # Try AI-based detection as fallback using simple text analysis
            system_prompt = """
            Analyse ce message utilisateur et détermine son intention principale. Réponds uniquement avec l'un de ces mots:
            - "summarize_email" si l'utilisateur veut résumer un email
            - "generate_reply" si l'utilisateur veut générer une réponse à un email  
            - "classify_email" si l'utilisateur veut classer/catégoriser un email
            - "conversation" pour tout autre cas (discussion, questions générales, etc.)
            
            Sois strict: choisis "conversation" si tu n'es pas sûr à 80% que c'est une demande email spécifique.
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Message: {user_message}"}
            ]
            
            response = self._make_request(messages)
            
            # Extract response content
            choice = response.get('choices', [{}])[0]
            message = choice.get('message', {})
            content = message.get('content', '').strip().lower()
            
            # Parse AI response
            if 'summarize_email' in content:
                intent = 'summarize_email'
                confidence = 0.8
            elif 'generate_reply' in content:
                intent = 'generate_reply'
                confidence = 0.8
            elif 'classify_email' in content:
                intent = 'classify_email'
                confidence = 0.8
            else:
                intent = 'conversation'
                confidence = 0.9
            
            logger.info(f"AI detected intent: {intent} with confidence: {confidence}")
            return {
                'success': True,
                'intent': intent,
                'confidence': confidence,
                'extracted_content': user_message,
                'reasoning': f'Détection IA: {content}'
            }
            
        except Exception as e:
            logger.error(f"Error detecting intent: {e}")
            return {
                'success': True,
                'intent': 'conversation',
                'confidence': 0.5,
                'reasoning': f'Error occurred, defaulting to conversation: {str(e)}'
            }

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
            
            # Add conversation history
            messages.extend(conversation_history)
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            response = self._make_request(messages)
            
            # Extract response content
            choice = response.get('choices', [{}])[0]
            message = choice.get('message', {})
            content = message.get('content', '').strip()
            
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

    def process_user_message(self, user_message: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Main entry point for processing user messages with intent detection and function calling.
        
        Args:
            user_message: The user's input message
            conversation_history: Previous conversation messages (optional)
            
        Returns:
            Dictionary containing the appropriate response based on detected intent
        """
        try:
            logger.info(f"Processing user message: {user_message[:100]}...")
            
            # Step 1: Detect user intent
            intent_result = self.detect_intent(user_message)
            
            if not intent_result.get('success'):
                return self.chat_conversation(user_message, conversation_history)
            
            intent = intent_result.get('intent', 'conversation')
            confidence = intent_result.get('confidence', 0.5)
            
            logger.info(f"Detected intent: {intent} with confidence: {confidence}")
            
            # Step 2: Route to appropriate handler based on intent
            if intent == 'conversation' or confidence < 0.7:
                # Default to conversation for low confidence or explicit conversation intent
                return self.chat_conversation(user_message, conversation_history)
            
            elif intent == 'summarize_email':
                # Extract content and summarize
                extracted_content = intent_result.get('extracted_content', user_message)
                result = self.summarize_mail(extracted_content, "user@frontend.com", "Email à résumer")
                
                if result.get('success'):
                    summary_data = result.get('summary', {})
                    if isinstance(summary_data, dict):
                        summary_text = summary_data.get('summary', 'Résumé généré avec succès.')
                    else:
                        summary_text = str(summary_data)
                    
                    return {
                        'success': True,
                        'response': f"📧 **Résumé de l'email:**\n\n{summary_text}",
                        'type': 'email_summary',
                        'function_used': 'summarize_mail',
                        'original_intent': intent
                    }
                else:
                    return {
                        'success': True,
                        'response': "Je n'ai pas pu résumer cet email. Pouvez-vous vérifier le contenu et réessayer ?",
                        'type': 'error',
                        'original_intent': intent
                    }
            
            elif intent == 'generate_reply':
                # Extract content and generate reply
                extracted_content = intent_result.get('extracted_content', user_message)
                result = self.generate_mail_answer(extracted_content, "", "professional", "french")
                
                if result.get('success'):
                    response_data = result.get('response', {})
                    if isinstance(response_data, dict):
                        reply_text = response_data.get('response', 'Réponse générée avec succès.')
                        subject = response_data.get('subject', 'Re: Votre email')
                        response_text = f"✉️ **Réponse proposée:**\n\n**Sujet:** {subject}\n\n{reply_text}"
                    else:
                        response_text = f"✉️ **Réponse proposée:**\n\n{str(response_data)}"
                    
                    return {
                        'success': True,
                        'response': response_text,
                        'type': 'email_reply',
                        'function_used': 'generate_mail_answer',
                        'original_intent': intent
                    }
                else:
                    return {
                        'success': True,
                        'response': "Je n'ai pas pu générer une réponse à cet email. Pouvez-vous vérifier le contenu et réessayer ?",
                        'type': 'error',
                        'original_intent': intent
                    }
            
            elif intent == 'classify_email':
                # Extract content and classify
                extracted_content = intent_result.get('extracted_content', user_message)
                result = self.classify_mail(extracted_content, "user@frontend.com", "Email à classer")
                
                if result.get('success'):
                    classification_data = result.get('classification', {})
                    if isinstance(classification_data, dict):
                        category = classification_data.get('category', 'Non classé')
                        confidence = classification_data.get('confidence', 0.5)
                        reasoning = classification_data.get('reasoning', 'Aucune explication disponible')
                        response_text = f"🏷️ **Classification de l'email:**\n\n**Catégorie:** {category}\n**Confiance:** {confidence:.0%}\n**Explication:** {reasoning}"
                    else:
                        response_text = f"🏷️ **Classification de l'email:**\n\n{str(classification_data)}"
                    
                    return {
                        'success': True,
                        'response': response_text,
                        'type': 'email_classification',
                        'function_used': 'classify_mail',
                        'original_intent': intent
                    }
                else:
                    return {
                        'success': True,
                        'response': "Je n'ai pas pu classer cet email. Pouvez-vous vérifier le contenu et réessayer ?",
                        'type': 'error',
                        'original_intent': intent
                    }
            
            else:
                # Fallback to conversation
                return self.chat_conversation(user_message, conversation_history)
                
        except Exception as e:
            logger.error(f"Error processing user message: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': 'Une erreur s\'est produite lors du traitement de votre message. Comment puis-je vous aider autrement ?',
                'type': 'error'
            }

    def _parse_summary_content(self, content: str) -> Dict[str, Any]:
        """
        Parse content response from Albert API to extract structured summary information.
        
        Args:
            content: Raw content response from Albert API
            
        Returns:
            Dictionary with structured summary data
        """
        # For Albert API content responses, we use the full content as summary
        # and try to extract some basic structure
        summary_data = {
            'summary': content,
            'key_points': [],
            'action_required': False,
            'urgency_level': 'medium'
        }
        
        # Try to extract key points if content is structured
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('- ') or line.startswith('• ') or ('**' in line and ':' in line):
                # Extract key points from bullet points or bold sections
                clean_point = line.replace('- ', '').replace('• ', '').replace('**', '').strip()
                if clean_point and len(clean_point) > 5:
                    summary_data['key_points'].append(clean_point)
        
        # Detect urgency keywords
        content_lower = content.lower()
        if any(word in content_lower for word in ['urgent', 'immédiat', 'critique', 'panne', 'problème']):
            summary_data['urgency_level'] = 'high'
            summary_data['action_required'] = True
        elif any(word in content_lower for word in ['demande', 'besoin', 'aide', 'support']):
            summary_data['action_required'] = True
            summary_data['urgency_level'] = 'medium'
        else:
            summary_data['urgency_level'] = 'low'
            
        return summary_data

    def _parse_classification_content(self, content: str, categories: List[str]) -> Dict[str, Any]:
        """
        Parse content response from Albert API to extract classification information.
        
        Args:
            content: Raw content response from Albert API
            categories: Available categories for classification
            
        Returns:
            Dictionary with classification data
        """
        content_lower = content.lower()
        
        # Try to extract category from content first - look for explicit classifications
        detected_category = 'normal'  # default
        confidence_score = 0.7  # default moderate confidence
        
        # Look for explicit category declarations (most reliable)
        if '**catégorie**' in content_lower:
            # Extract the category mentioned after **catégorie**
            lines = content.split('\n')
            for line in lines:
                if '**catégorie**' in line.lower():
                    if 'information' in line.lower():
                        detected_category = 'information'
                        confidence_score = 0.9
                    elif 'urgent' in line.lower():
                        detected_category = 'urgent'
                        confidence_score = 0.9
                    elif 'request' in line.lower() or 'demande' in line.lower():
                        detected_category = 'request'
                        confidence_score = 0.9
                    elif 'complaint' in line.lower() or 'plainte' in line.lower():
                        detected_category = 'complaint'
                        confidence_score = 0.9
                    elif 'support' in line.lower():
                        detected_category = 'support'
                        confidence_score = 0.9
                    elif 'low_priority' in line.lower() or 'faible' in line.lower():
                        detected_category = 'low_priority'
                        confidence_score = 0.9
                    elif 'spam' in line.lower():
                        detected_category = 'spam'
                        confidence_score = 0.9
                    break
        
        # If no explicit category found, look for patterns in the content
        if detected_category == 'normal':
            # Look for content patterns rather than individual keywords
            if 'félicitation' in content_lower and 'excellent' in content_lower:
                detected_category = 'low_priority'  # positive feedback
                confidence_score = 0.8
            elif 'panne' in content_lower and 'urgent' in content_lower:
                detected_category = 'urgent'
                confidence_score = 0.9
            elif 'information' in content_lower and 'fournit' in content_lower:
                detected_category = 'information'
                confidence_score = 0.8
            elif 'demande' in content_lower and 'aide' in content_lower:
                detected_category = 'request'
                confidence_score = 0.8
        
        # Ensure detected category is in available categories
        available_cats = [cat.value if hasattr(cat, 'value') else str(cat) for cat in categories]
        if detected_category not in available_cats:
            detected_category = 'normal'
            confidence_score = 0.5
        
        classification_data = {
            'primary_category': detected_category,
            'confidence_score': confidence_score,
            'reasoning': f'Classification basée sur l\'analyse du contenu: {content[:100]}...',
            'content_analysis': content
        }
        
        return classification_data

    def _parse_answer_content(self, content: str, tone: str) -> Dict[str, Any]:
        """
        Parse content response from Albert API to extract answer information.
        
        Args:
            content: Raw content response from Albert API
            tone: Requested tone for the response
            
        Returns:
            Dictionary with response data
        """
        # Generate a subject based on content and tone
        content_lines = content.strip().split('\n')
        first_line = content_lines[0] if content_lines else content
        
        # Generate appropriate subject
        if 'merci' in content.lower():
            subject = 'Réponse à votre message'
        elif 'information' in content.lower():
            subject = 'Informations demandées'
        elif 'aide' in content.lower() or 'support' in content.lower():
            subject = 'Support technique'
        else:
            subject = 'Réponse'
        
        response_data = {
            'response': content,
            'subject': subject,
            'tone_used': tone,
            'content_type': 'generated_response'
        }
        
        return response_data

# Global instance for easy access
chatbot = AlbertChatbot()


def get_chatbot() -> AlbertChatbot:
    """
    Get the global chatbot instance.
    
    Returns:
        AlbertChatbot instance
    """
    return chatbot


