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
import time
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
        Make a request to Albert API with optional function calling.
        
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
            
            # Add function calling parameters if functions are provided
            if functions:
                payload["tools"] = [{"type": "function", "function": func} for func in functions]
                payload["tool_choice"] = "auto"  # Let the model decide when to use tools
            
            logger.info(f"Making request to Albert API with {len(messages)} messages")
            if functions:
                logger.info(f"Including {len(functions)} available tools")
            
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
                              "Tu DOIS utiliser la fonction summarize_email pour analyser le contenu des emails. "
                              "Ne réponds jamais directement sans utiliser cette fonction."
                },
                {
                    "role": "user",
                    "content": f"Utilise la fonction summarize_email pour analyser cet email:\n\n{mail_context}"
                }
            ]
            
            response = self._make_request(messages, functions)
            
            # Extract function call result or content response
            choice = response.get('choices', [{}])[0]
            message = choice.get('message', {})
            
            # Check for new tool_calls format first
            if 'tool_calls' in message and message['tool_calls']:
                tool_call = message['tool_calls'][0]
                if tool_call['type'] == 'function':
                    function_call = tool_call['function']
                    if function_call['name'] == 'summarize_email':
                        summary_data = json.loads(function_call['arguments'])
                        logger.info("Successfully summarized email using function call")
                        return {
                            'success': True,
                            'summary': summary_data,
                            'original_sender': sender,
                            'original_subject': subject
                        }
            
            # Check for legacy function_call format
            elif 'function_call' in message:
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
            content = message.get('content', '')
            if content:
                content = content.strip()
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
            Tu DOIS utiliser la fonction generate_email_response pour générer des réponses aux emails.
            Ne réponds jamais directement sans utiliser cette fonction.
            
            Génère des réponses appropriées en {language} avec un ton {tone}.
            Assure-toi que tes réponses sont:
            - Claires et concises
            - Respectueuses et professionnelles
            - Adaptées au contexte
            - Bien structurées
            """
            
            user_prompt = f"""
            Utilise la fonction generate_email_response pour générer une réponse à cet email:
            
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
            
            # Check for new tool_calls format first
            if 'tool_calls' in message and message['tool_calls']:
                tool_call = message['tool_calls'][0]
                if tool_call['type'] == 'function':
                    function_call = tool_call['function']
                    if function_call['name'] == 'generate_email_response':
                        response_data = json.loads(function_call['arguments'])
                        logger.info("Successfully generated email response using function call")
                        return {
                            'success': True,
                            'response': response_data,
                            'context_used': context,
                            'tone_requested': tone
                        }
            
            # Check for legacy function_call format
            elif 'function_call' in message:
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
            content = message.get('content', '')
            if content:
                content = content.strip()
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
            Tu DOIS utiliser la fonction classify_email pour analyser et classer les emails.
            Ne réponds jamais directement sans utiliser cette fonction.
            
            Tu dois analyser le contenu, l'expéditeur et le sujet des emails pour les classer 
            dans les catégories suivantes: {', '.join(categories)}.
            
            Fournis toujours une justification claire de tes classifications.
            """
            
            user_prompt = f"""
            Utilise la fonction classify_email pour classifier cet email selon les catégories disponibles:
            
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
            
            # Check for new tool_calls format first
            if 'tool_calls' in message and message['tool_calls']:
                tool_call = message['tool_calls'][0]
                if tool_call['type'] == 'function':
                    function_call = tool_call['function']
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
            
            # Check for legacy function_call format
            elif 'function_call' in message:
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
            content = message.get('content', '')
            if content:
                content = content.strip()
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

    def _get_email_tools(self) -> List[Dict[str, Any]]:
        """
        Define available email processing tools for function calling.
        
        Returns:
            List of tool definitions for Albert API function calling
        """
        return [
            {
                "name": "summarize_email",
                "description": "Résume le contenu d'un email en français avec les points clés et le niveau d'urgence",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email_content": {
                            "type": "string",
                            "description": "Le contenu de l'email à résumer"
                        },
                        "sender": {
                            "type": "string", 
                            "description": "L'expéditeur de l'email"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Le sujet de l'email"
                        }
                    },
                    "required": ["email_content"]
                }
            },
            {
                "name": "generate_email_reply",
                "description": "Génère une réponse professionnelle à un email",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "original_email": {
                            "type": "string",
                            "description": "Le contenu de l'email original auquel répondre"
                        },
                        "context": {
                            "type": "string",
                            "description": "Contexte supplémentaire pour la réponse"
                        },
                        "tone": {
                            "type": "string",
                            "enum": ["professional", "friendly", "formal"],
                            "description": "Le ton souhaité pour la réponse"
                        }
                    },
                    "required": ["original_email"]
                }
            },
            {
                "name": "classify_email",
                "description": "Classifie un email selon différentes catégories (urgent, normal, information, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email_content": {
                            "type": "string",
                            "description": "Le contenu de l'email à classifier"
                        },
                        "sender": {
                            "type": "string",
                            "description": "L'expéditeur de l'email"
                        },
                        "subject": {
                            "type": "string", 
                            "description": "Le sujet de l'email"
                        }
                    },
                    "required": ["email_content"]
                }
            },
            {
                "name": "search_emails",
                "description": "Recherche des emails dans la boîte mail de l'utilisateur",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Termes de recherche pour trouver des emails"
                        },
                        "mailbox_id": {
                            "type": "string",
                            "description": "ID de la boîte mail spécifique (optionnel)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Nombre maximum d'emails à retourner",
                            "default": 10
                        },
                        "use_elasticsearch": {
                            "type": "boolean",
                            "description": "Utiliser Elasticsearch pour la recherche",
                            "default": True
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "search_threads",
                "description": "Recherche des conversations (threads) dans la boîte mail de l'utilisateur",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Termes de recherche pour trouver des conversations"
                        },
                        "mailbox_id": {
                            "type": "string",
                            "description": "ID de la boîte mail spécifique (optionnel)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Nombre maximum de conversations à retourner",
                            "default": 10
                        },
                        "filters": {
                            "type": "object",
                            "description": "Filtres additionnels (has_unread, has_starred, etc.)",
                            "properties": {
                                "has_unread": {"type": "boolean"},
                                "has_starred": {"type": "boolean"},
                                "has_draft": {"type": "boolean"}
                            }
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_recent_emails",
                "description": "Récupère les emails récents de l'utilisateur",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Nombre de jours en arrière pour récupérer les emails",
                            "default": 7
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Nombre maximum d'emails à retourner",
                            "default": 10
                        }
                    }
                }
            },
            {
                "name": "get_unread_emails",
                "description": "Récupère les emails non lus de l'utilisateur",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Nombre maximum d'emails à retourner",
                            "default": 20
                        }
                    }
                }
            },
            {
                "name": "get_user_mailboxes",
                "description": "Récupère les boîtes mail accessibles à l'utilisateur",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_thread_statistics",
                "description": "Récupère les statistiques des conversations de l'utilisateur",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mailbox_id": {
                            "type": "string",
                            "description": "ID de la boîte mail spécifique (optionnel)"
                        }
                    }
                }
            },
            {
                "name": "create_draft_email",
                "description": "Crée un brouillon d'email",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "subject": {
                            "type": "string",
                            "description": "Sujet de l'email"
                        },
                        "body": {
                            "type": "string",
                            "description": "Contenu du corps de l'email"
                        },
                        "recipients_to": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "email": {"type": "string"},
                                    "name": {"type": "string"}
                                },
                                "required": ["email"]
                            },
                            "description": "Liste des destinataires principaux"
                        },
                        "recipients_cc": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "email": {"type": "string"},
                                    "name": {"type": "string"}
                                },
                                "required": ["email"]
                            },
                            "description": "Liste des destinataires en copie (optionnel)"
                        },
                        "recipients_bcc": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "email": {"type": "string"},
                                    "name": {"type": "string"}
                                },
                                "required": ["email"]
                            },
                            "description": "Liste des destinataires en copie cachée (optionnel)"
                        },
                        "mailbox_id": {
                            "type": "string",
                            "description": "ID de la boîte mail expéditrice (optionnel, utilise la première disponible si non spécifiée)"
                        }
                    },
                    "required": ["subject", "body", "recipients_to"]
                }
            },
            {
                "name": "send_email",
                "description": "Envoie un email immédiatement",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "subject": {
                            "type": "string",
                            "description": "Sujet de l'email"
                        },
                        "body": {
                            "type": "string",
                            "description": "Contenu du corps de l'email"
                        },
                        "recipients_to": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "email": {"type": "string"},
                                    "name": {"type": "string"}
                                },
                                "required": ["email"]
                            },
                            "description": "Liste des destinataires principaux"
                        },
                        "recipients_cc": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "email": {"type": "string"},
                                    "name": {"type": "string"}
                                },
                                "required": ["email"]
                            },
                            "description": "Liste des destinataires en copie (optionnel)"
                        },
                        "recipients_bcc": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "email": {"type": "string"},
                                    "name": {"type": "string"}
                                },
                                "required": ["email"]
                            },
                            "description": "Liste des destinataires en copie cachée (optionnel)"
                        },
                        "mailbox_id": {
                            "type": "string",
                            "description": "ID de la boîte mail expéditrice (optionnel, utilise la première disponible si non spécifiée)"
                        },
                        "draft_message_id": {
                            "type": "string",
                            "description": "ID d'un brouillon existant à envoyer (optionnel)"
                        }
                    },
                    "required": ["subject", "body", "recipients_to"]
                }
            },
            {
                "name": "reply_to_email",
                "description": "Répond à un email existant",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "original_message_id": {
                            "type": "string",
                            "description": "ID du message original auquel répondre"
                        },
                        "body": {
                            "type": "string",
                            "description": "Contenu de la réponse"
                        },
                        "reply_all": {
                            "type": "boolean",
                            "description": "Répondre à tous les destinataires",
                            "default": False
                        },
                        "as_draft": {
                            "type": "boolean",
                            "description": "Sauvegarder comme brouillon au lieu d'envoyer",
                            "default": False
                        }
                    },
                    "required": ["original_message_id", "body"]
                }
            },
            {
                "name": "forward_email",
                "description": "Transfère un email existant",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "original_message_id": {
                            "type": "string",
                            "description": "ID du message original à transférer"
                        },
                        "recipients_to": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "email": {"type": "string"},
                                    "name": {"type": "string"}
                                },
                                "required": ["email"]
                            },
                            "description": "Liste des destinataires pour le transfert"
                        },
                        "body": {
                            "type": "string",
                            "description": "Message additionnel à ajouter avant le transfert (optionnel)"
                        },
                        "recipients_cc": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "email": {"type": "string"},
                                    "name": {"type": "string"}
                                },
                                "required": ["email"]
                            },
                            "description": "Liste des destinataires en copie (optionnel)"
                        },
                        "as_draft": {
                            "type": "boolean",
                            "description": "Sauvegarder comme brouillon au lieu d'envoyer",
                            "default": False
                        }
                    },
                    "required": ["original_message_id", "recipients_to"]
                }
            },
            {
                "name": "delete_draft",
                "description": "Supprime un brouillon d'email",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "draft_message_id": {
                            "type": "string",
                            "description": "ID du brouillon à supprimer"
                        }
                    },
                    "required": ["draft_message_id"]
                }
            },
            {
                "name": "retrieve_email_content",
                "description": "Récupère le contenu complet de l'email qui correspond le mieux à la requête de l'utilisateur",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Requête de l'utilisateur pour trouver l'email le plus pertinent"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Nombre maximum d'emails à rechercher",
                            "default": 5
                        },
                        "use_elasticsearch": {
                            "type": "boolean",
                            "description": "Utiliser Elasticsearch pour la recherche",
                            "default": True
                        }
                    },
                    "required": ["query"]
                }
            }
        ]

    def _execute_email_function(self, function_name: str, arguments: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
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
            # Log the function call details
            logger.info(f"🔧 Executing function: {function_name}")
            logger.info(f"📝 Function arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}")
            logger.info(f"👤 User ID: {user_id}")
            
            # Log argument types and values for debugging
            for key, value in arguments.items():
                value_type = type(value).__name__
                if isinstance(value, str):
                    value_preview = value[:100] + "..." if len(value) > 100 else value
                    logger.debug(f"  - {key} ({value_type}): {value_preview}")
                elif isinstance(value, (list, dict)):
                    logger.debug(f"  - {key} ({value_type}): {len(value)} items")
                else:
                    logger.debug(f"  - {key} ({value_type}): {value}")
            
            execution_start_time = time.time()
            logger.info(f"🔧 _execute_email_function called: function={function_name}, user_id={user_id}")
            logger.info(f"📝 Function arguments received: {arguments}")
            logger.debug(f"📊 Argument details: {[(k, type(v).__name__, len(str(v)) if isinstance(v, (str, list, dict)) else v) for k, v in arguments.items()]}")
            
            if function_name == "summarize_email":
                email_content = arguments.get("email_content", "")
                sender = arguments.get("sender", "")
                subject = arguments.get("subject", "")
                
                logger.info(f"📧 summarize_email - email_content length: {len(email_content)}, sender: '{sender}', subject: '{subject}'")
                logger.debug(f"📧 summarize_email - email_content preview: {email_content[:200]}...")
                
                result = self.summarize_mail(email_content, sender, subject)
                
                # Check if the underlying function was successful
                execution_time = time.time() - execution_start_time
                if result.get('success'):
                    logger.info(f"✅ summarize_email completed successfully (took {execution_time:.2f}s)")
                    logger.info(f"📊 Result summary: {len(result.get('response', ''))} characters in response")
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
                
            elif function_name == "generate_email_reply":
                original_email = arguments.get("original_email", "")
                context = arguments.get("context", "")
                tone = arguments.get("tone", "professional")
                
                logger.info(f"✉️ generate_email_reply - original_email length: {len(original_email)}, context: '{context}', tone: '{tone}'")
                logger.debug(f"✉️ generate_email_reply - original_email preview: {original_email[:200]}...")
                
                result = self.generate_mail_answer(original_email, context, tone)
                
                # Check if the underlying function was successful
                execution_time = time.time() - execution_start_time
                if result.get('success'):
                    logger.info(f"✅ generate_email_reply completed successfully (took {execution_time:.2f}s)")
                    logger.info(f"📊 Reply generated: {len(result.get('response', {}).get('response', ''))} characters")
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
                
            elif function_name == "classify_email":
                email_content = arguments.get("email_content", "")
                sender = arguments.get("sender", "")
                subject = arguments.get("subject", "")
                
                result = self.classify_mail(email_content, sender, subject)
                
                # Check if the underlying function was successful
                if result.get('success'):
                    return {
                        "success": True,
                        "function": "classify_email",
                        "result": result
                    }
                else:
                    return {
                        "success": False,
                        "function": "classify_email",
                        "error": result.get('error', 'Error in classify_mail'),
                        "result": result
                    }
                
            elif function_name == "search_emails":
                # Import email retrieval functions
                from .email_retrieval import search_messages
                
                query = arguments.get("query", "")
                mailbox_id = arguments.get("mailbox_id")
                limit = arguments.get("limit", 10)
                use_elasticsearch = arguments.get("use_elasticsearch", True)
                
                if not user_id:
                    return {"success": False, "error": "User ID required for email search"}
                
                results = search_messages(
                    user_id=user_id, 
                    query=query, 
                    mailbox_id=mailbox_id,
                    limit=limit,
                    use_elasticsearch=use_elasticsearch
                )
                return {
                    "success": True,
                    "function": "search_emails",
                    "result": {"emails": results, "count": len(results)}
                }
                
            elif function_name == "search_threads":
                # Import thread search function
                from .email_retrieval import search_threads_for_chatbot
                
                query = arguments.get("query", "")
                mailbox_id = arguments.get("mailbox_id")
                limit = arguments.get("limit", 10)
                filters = arguments.get("filters", {})
                
                if not user_id:
                    return {"success": False, "error": "User ID required for thread search"}
                
                results = search_threads_for_chatbot(
                    user_id=user_id,
                    query=query,
                    mailbox_id=mailbox_id,
                    limit=limit,
                    filters=filters
                )
                return {
                    "success": True,
                    "function": "search_threads",
                    "result": {"threads": results, "count": len(results)}
                }
                
            elif function_name == "get_recent_emails":
                # Import email retrieval functions
                from .email_retrieval import get_recent_messages
                
                days = arguments.get("days", 7)
                limit = arguments.get("limit", 10)
                
                logger.info(f"get_recent_emails called with: user_id={user_id}, days={days}, limit={limit}")
                logger.debug(f"Arguments received: {arguments}")
                
                if not user_id:
                    logger.error("get_recent_emails: User ID is missing")
                    return {"success": False, "error": "User ID required for email retrieval"}
                
                try:
                    logger.info(f"Calling get_recent_messages with user_id={user_id}, days={days}, limit={limit}")
                    results = get_recent_messages(user_id=user_id, days=days, limit=limit)
                    logger.info(f"get_recent_messages returned {len(results)} results")
                    logger.debug(f"Results sample: {results[:2] if results else 'No results'}")
                    
                    return {
                        "success": True,
                        "function": "get_recent_emails",
                        "result": {"emails": results, "count": len(results)}
                    }
                except Exception as e:
                    logger.error(f"Error in get_recent_emails: {e}", exc_info=True)
                    return {"success": False, "error": f"Error retrieving recent emails: {str(e)}"}
                
            elif function_name == "get_unread_emails":
                # Import email retrieval functions
                from .email_retrieval import get_unread_messages
                
                limit = arguments.get("limit", 20)
                
                if not user_id:
                    return {"success": False, "error": "User ID required for email retrieval"}
                
                results = get_unread_messages(user_id=user_id, limit=limit)
                return {
                    "success": True,
                    "function": "get_unread_emails",
                    "result": {"emails": results, "count": len(results)}
                }
                
            elif function_name == "get_user_mailboxes":
                # Import mailbox retrieval function
                from .email_retrieval import get_user_accessible_mailboxes
                
                if not user_id:
                    return {"success": False, "error": "User ID required for mailbox retrieval"}
                
                results = get_user_accessible_mailboxes(user_id=user_id)
                mailbox_list = []
                for mailbox in results:
                    mailbox_list.append({
                        'id': str(mailbox.id),
                        'email': f"{mailbox.local_part}@{mailbox.domain.name}",
                        'domain': mailbox.domain.name,
                        'local_part': mailbox.local_part,
                        'contact_name': mailbox.contact.name if mailbox.contact else None
                    })
                
                return {
                    "success": True,
                    "function": "get_user_mailboxes",
                    "result": {"mailboxes": mailbox_list, "count": len(mailbox_list)}
                }
                
            elif function_name == "get_thread_statistics":
                # Import statistics function
                from .email_retrieval import get_thread_statistics
                
                mailbox_id = arguments.get("mailbox_id")
                
                if not user_id:
                    return {"success": False, "error": "User ID required for statistics"}
                
                results = get_thread_statistics(user_id=user_id, mailbox_id=mailbox_id)
                return {
                    "success": True,
                    "function": "get_thread_statistics",
                    "result": results
                }
                
            elif function_name == "retrieve_email_content":
                # Import email retrieval function
                from .email_retrieval import retrieve_email_content_by_query
                
                query = arguments.get("query", "")
                limit = arguments.get("limit", 5)
                use_elasticsearch = arguments.get("use_elasticsearch", True)
                
                logger.info(f"🔍 retrieve_email_content - query: '{query}', limit: {limit}, use_elasticsearch: {use_elasticsearch}")
                
                if not user_id:
                    logger.error("❌ retrieve_email_content - User ID is required but missing")
                    return {"success": False, "error": "User ID required for email content retrieval"}
                
                if not query:
                    logger.error("❌ retrieve_email_content - Query is required but empty")
                    return {"success": False, "error": "Query is required for email content retrieval"}
                
                logger.info(f"🔍 retrieve_email_content - Executing query for user {user_id}")
                result = retrieve_email_content_by_query(
                    user_id=user_id, 
                    query=query, 
                    limit=limit,
                    use_elasticsearch=use_elasticsearch
                )
                
                logger.info(f"🔍 retrieve_email_content - Result success: {result.get('success')}")
                if result.get('success'):
                    metadata = result.get('metadata', {})
                    logger.info(f"🔍 retrieve_email_content - Email found: '{metadata.get('subject', 'No subject')}' from {metadata.get('sender_name', 'Unknown')}")
                else:
                    logger.warning(f"🔍 retrieve_email_content - Failed: {result.get('error', 'Unknown error')}")
                
                # Check if the underlying function was successful
                if result.get('success'):
                    return {
                        "success": True,
                        "function": "retrieve_email_content",
                        "result": result
                    }
                else:
                    return {
                        "success": False,
                        "function": "retrieve_email_content",
                        "error": result.get('error', 'Error in retrieve_email_content_by_query'),
                        "result": result
                    }
                
            elif function_name == "create_draft_email":
                # Import email writing functions
                from .email_writer import create_draft_email
                
                subject = arguments.get("subject", "")
                body = arguments.get("body", "")
                recipients_to = arguments.get("recipients_to", [])
                recipients_cc = arguments.get("recipients_cc", [])
                recipients_bcc = arguments.get("recipients_bcc", [])
                mailbox_id = arguments.get("mailbox_id")
                
                logger.info(f"📝 create_draft_email - subject: '{subject}', body length: {len(body)}")
                logger.info(f"📝 create_draft_email - recipients_to: {len(recipients_to)} recipient(s): {[r.get('email', r) for r in recipients_to]}")
                logger.info(f"📝 create_draft_email - recipients_cc: {len(recipients_cc)}, recipients_bcc: {len(recipients_bcc)}")
                logger.info(f"📝 create_draft_email - mailbox_id: {mailbox_id}")
                logger.debug(f"📝 create_draft_email - body preview: {body[:200]}...")
                
                if not user_id:
                    logger.error("❌ create_draft_email - User ID is required but missing")
                    return {"success": False, "error": "User ID required for creating draft email"}
                
                # If no mailbox specified, get user's first available mailbox
                if not mailbox_id:
                    logger.info("📝 create_draft_email - No mailbox specified, finding user's available mailboxes")
                    from .email_writer import get_user_mailboxes
                    user_mailboxes = get_user_mailboxes(user_id)
                    logger.info(f"📝 create_draft_email - Found {len(user_mailboxes)} mailbox(es) for user")
                    
                    if not user_mailboxes:
                        logger.error("❌ create_draft_email - No accessible mailboxes found for user")
                        return {"success": False, "error": "No accessible mailboxes found"}
                    
                    # Find first mailbox with send permissions
                    sender_mailbox = None
                    for mb in user_mailboxes:
                        if mb.get('can_send', False):
                            sender_mailbox = mb
                            break
                    
                    if not sender_mailbox:
                        logger.error("❌ create_draft_email - No mailboxes with send permissions found")
                        return {"success": False, "error": "No mailboxes with send permissions found"}
                    
                    mailbox_id = sender_mailbox['id']
                    logger.info(f"📝 create_draft_email - Using mailbox: {mailbox_id}")
                
                logger.info(f"📝 create_draft_email - Creating draft with mailbox {mailbox_id}")
                result = create_draft_email(
                    user_id=user_id,
                    mailbox_id=mailbox_id,
                    subject=subject,
                    body=body,
                    recipients_to=recipients_to,
                    recipients_cc=recipients_cc,
                    recipients_bcc=recipients_bcc
                )
                
                logger.info(f"📝 create_draft_email - Result success: {result.get('success')}")
                if result.get('success'):
                    logger.info(f"📝 create_draft_email - Draft created with ID: {result.get('message_id')}")
                else:
                    logger.warning(f"📝 create_draft_email - Failed: {result.get('error', 'Unknown error')}")
                return {
                    "success": True,
                    "function": "create_draft_email",
                    "result": result
                }
                
            elif function_name == "send_email":
                # Import email writing functions
                from .email_writer import send_email
                
                subject = arguments.get("subject", "")
                body = arguments.get("body", "")
                recipients_to = arguments.get("recipients_to", [])
                recipients_cc = arguments.get("recipients_cc", [])
                recipients_bcc = arguments.get("recipients_bcc", [])
                mailbox_id = arguments.get("mailbox_id")
                draft_message_id = arguments.get("draft_message_id")
                
                if not user_id:
                    return {"success": False, "error": "User ID required for sending email"}
                
                # If no mailbox specified, get user's first available mailbox
                if not mailbox_id and not draft_message_id:
                    from .email_writer import get_user_mailboxes
                    user_mailboxes = get_user_mailboxes(user_id)
                    if not user_mailboxes:
                        return {"success": False, "error": "No accessible mailboxes found"}
                    
                    # Find first mailbox with send permissions
                    sender_mailbox = None
                    for mb in user_mailboxes:
                        if mb.get('can_send', False):
                            sender_mailbox = mb
                            break
                    
                    if not sender_mailbox:
                        return {"success": False, "error": "No mailboxes with send permissions found"}
                    
                    mailbox_id = sender_mailbox['id']
                
                result = send_email(
                    user_id=user_id,
                    mailbox_id=mailbox_id,
                    subject=subject,
                    body=body,
                    recipients_to=recipients_to,
                    recipients_cc=recipients_cc,
                    recipients_bcc=recipients_bcc,
                    draft_message_id=draft_message_id
                )
                return {
                    "success": True,
                    "function": "send_email",
                    "result": result
                }
                
            elif function_name == "reply_to_email":
                # Import email writing functions
                from .email_writer import reply_to_email
                
                original_message_id = arguments.get("original_message_id", "")
                body = arguments.get("body", "")
                reply_all = arguments.get("reply_all", False)
                as_draft = arguments.get("as_draft", False)
                
                if not user_id:
                    return {"success": False, "error": "User ID required for replying to email"}
                
                result = reply_to_email(
                    user_id=user_id,
                    original_message_id=original_message_id,
                    body=body,
                    reply_all=reply_all,
                    as_draft=as_draft
                )
                return {
                    "success": True,
                    "function": "reply_to_email",
                    "result": result
                }
                
            elif function_name == "forward_email":
                # Import email writing functions
                from .email_writer import forward_email
                
                original_message_id = arguments.get("original_message_id", "")
                recipients_to = arguments.get("recipients_to", [])
                body = arguments.get("body", "")
                recipients_cc = arguments.get("recipients_cc", [])
                as_draft = arguments.get("as_draft", False)
                
                if not user_id:
                    return {"success": False, "error": "User ID required for forwarding email"}
                
                result = forward_email(
                    user_id=user_id,
                    original_message_id=original_message_id,
                    recipients_to=recipients_to,
                    body=body,
                    recipients_cc=recipients_cc,
                    as_draft=as_draft
                )
                return {
                    "success": True,
                    "function": "forward_email",
                    "result": result
                }
                
            elif function_name == "delete_draft":
                # Import email writing functions
                from .email_writer import delete_draft
                
                draft_message_id = arguments.get("draft_message_id", "")
                
                if not user_id:
                    return {"success": False, "error": "User ID required for deleting draft"}
                
                result = delete_draft(
                    user_id=user_id,
                    draft_message_id=draft_message_id
                )
                return {
                    "success": True,
                    "function": "delete_draft",
                    "result": result
                }
                
            else:
                logger.warning(f"❌ Unknown function requested: {function_name}")
                logger.warning(f"📝 Available functions: summarize_email, generate_email_reply, classify_email, search_emails, search_threads, get_recent_emails, get_unread_emails, get_user_mailboxes, get_thread_statistics, retrieve_email_content, create_draft_email, send_email, reply_to_email, forward_email")
                return {
                    "success": False,
                    "error": f"Unknown function: {function_name}"
                }
                
        except Exception as e:
            execution_time = time.time() - execution_start_time
            logger.error(f"❌ Function execution failed: {function_name} (took {execution_time:.2f}s)")
            logger.error(f"📝 Arguments: {json.dumps(arguments, indent=2, ensure_ascii=False)}")
            logger.error(f"💥 Error: {str(e)}")
            logger.error(f"🔍 Full traceback:", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "function": function_name,
                "arguments": arguments,
                "execution_time": execution_time
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
            logger.info(f"process_user_message called with: user_id={user_id}, message='{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
            logger.debug(f"Full user message: {user_message}")
            logger.debug(f"Conversation history length: {len(conversation_history) if conversation_history else 0}")
            
            if conversation_history is None:
                conversation_history = []
            
            # Use intelligent multi-step function calling approach
            multi_step_result = self._handle_multi_step_functions(user_message, user_id, conversation_history)
            if multi_step_result is not None:
                return multi_step_result
            
            # System prompt for the AI assistant with enhanced multi-step function calling
            system_prompt = """
            Tu es un assistant intelligent spécialisé dans la gestion d'emails avec des capacités de fonction calling avancées.
            
            APPROCHE INTELLIGENTE - FONCTION CHAINING:
            Pour les demandes complexes, tu peux appeler plusieurs fonctions en séquence. Voici les workflows typiques:
            
            🔄 WORKFLOWS AUTOMATIQUES:
            
            1. "Résume l'email de [personne] sur [sujet]":
               → retrieve_email_content(query="personne sujet")
               → summarize_email(email_content=contenu_récupéré)
            
            2. "Réponds à l'email de [personne]":
               → retrieve_email_content(query="personne")  
               → generate_email_reply(original_email=contenu_récupéré)
               → create_draft_email(body=réponse_générée)
            
            3. "Classifie l'email sur [sujet]":
               → retrieve_email_content(query="sujet")
               → classify_email(email_content=contenu_récupéré)
            
            OUTILS DISPONIBLES:
            📥 RÉCUPÉRATION: retrieve_email_content, search_emails, search_threads, get_recent_emails, get_unread_emails
            🔍 ANALYSE: summarize_email, classify_email, get_thread_statistics  
            ✍️ GÉNÉRATION: generate_email_reply
            📧 ACTIONS: create_draft_email, send_email, reply_to_email, forward_email, delete_draft
            ⚙️ GESTION: get_user_mailboxes
            
            RÈGLES INTELLIGENTES:
            ✅ TOUJOURS commencer par retrieve_email_content si l'utilisateur mentionne un email spécifique
            ✅ ENCHAÎNER automatiquement les fonctions selon le besoin
            ✅ Utiliser les résultats d'une fonction comme entrée pour la suivante
            ✅ Pour les réponses, TOUJOURS créer un brouillon avec create_draft_email
            ✅ Être proactif - si l'utilisateur dit "réponds à l'email de Jean", faire retrieve→generate→create_draft automatiquement
            
            STRATÉGIE:
            - Analyse la demande de l'utilisateur
            - Identifie la séquence de fonctions nécessaire
            - Exécute les fonctions dans l'ordre logique
            - Utilise le contexte des résultats précédents
            
            Pour les conversations générales sans action email, réponds normalement sans utiliser de fonctions.
            """
            
            # Build messages for the conversation
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_message})
            
            # Get available tools
            tools = self._get_email_tools()
            logger.info(f"Available tools: {len(tools)} tools loaded")
            logger.debug(f"Tool names: {[tool['name'] for tool in tools]}")
            
            # Make request to Albert API with function calling
            logger.info("Making request to Albert API with function calling enabled")
            response = self._make_request(messages, tools)
            logger.debug(f"Albert API response keys: {list(response.keys()) if response else 'No response'}")
            
            # Process the response
            choice = response.get('choices', [{}])[0]
            message = choice.get('message', {})
            logger.debug(f"Response message keys: {list(message.keys()) if message else 'No message'}")
            
            # Check if AI wants to call a function
            if 'tool_calls' in message and message['tool_calls']:
                logger.info(f"AI wants to call {len(message['tool_calls'])} tool(s)")
                # Handle multiple tool calls if needed
                tool_call = message['tool_calls'][0]  # Take the first tool call
                logger.debug(f"Tool call: {tool_call}")
                
                if tool_call['type'] == 'function':
                    function_call = tool_call['function']
                    function_name = function_call['name']
                    
                    logger.info(f"AI wants to call function: {function_name}")
                    logger.debug(f"Raw function arguments: {function_call.get('arguments', 'No arguments')}")
                    
                    try:
                        function_args = json.loads(function_call['arguments'])
                        logger.info(f"✅ Successfully parsed function arguments:")
                        for key, value in function_args.items():
                            if isinstance(value, str) and len(value) > 100:
                                logger.info(f"  - {key}: '{value[:100]}...' ({len(value)} chars)")
                            elif isinstance(value, (list, dict)):
                                logger.info(f"  - {key}: {type(value).__name__} with {len(value)} items")
                            else:
                                logger.info(f"  - {key}: {value}")
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Failed to parse function arguments: {e}")
                        logger.error(f"Raw arguments were: {function_call.get('arguments', 'None')}")
                        return {
                            'success': False,
                            'response': "Erreur lors de l'analyse des paramètres de la fonction.",
                            'type': 'error'
                        }
                    
                    # Execute the function
                    logger.info(f"Executing function {function_name} with user_id={user_id}")
                    function_result = self._execute_email_function(function_name, function_args, user_id)
                    logger.info(f"Function {function_name} execution result: success={function_result.get('success')}")
                    
                    if function_result.get('success'):
                        logger.info(f"Function {function_name} succeeded, formatting response")
                        # Format the response based on the function used
                        return self._format_function_response(function_name, function_result, user_message)
                    else:
                        logger.error(f"Function {function_name} failed: {function_result.get('error')}")
                        return {
                            'success': False,
                            'response': f"Erreur lors de l'exécution de {function_name}: {function_result.get('error', 'Erreur inconnue')}",
                            'type': 'error',
                            'function_used': function_name
                        }
            
            # Fallback: check for legacy function_call format (just in case)
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
                function_result = self._execute_email_function(function_name, function_args, user_id)
                
                if function_result.get('success'):
                    # Format the response based on the function used
                    return self._format_function_response(function_name, function_result, user_message)
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
            
        except Exception as e:
            logger.error(f"Error processing user message: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': 'Une erreur s\'est produite lors du traitement de votre message. Comment puis-je vous aider autrement ?',
                'type': 'error'
            }

    def _format_function_response(self, function_name: str, function_result: Dict[str, Any], original_message: str) -> Dict[str, Any]:
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
            
            elif function_name == 'generate_email_reply':
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
            
            elif function_name == 'classify_email':
                if result_data.get('success'):
                    classification = result_data.get('classification', {})
                    if isinstance(classification, dict):
                        category = classification.get('primary_category', 'Non classé')
                        confidence = classification.get('confidence_score', 0.5)
                        response_text = f"🏷️ **Classification de l'email:**\n\n**Catégorie:** {category}\n**Confiance:** {confidence:.0%}\n**Explication:** {reasoning}"
                    else:
                        response_text = f"🏷️ **Classification de l'email:**\n\n{str(classification_data)}"
                else:
                    response_text = "Je n'ai pas pu classifier cet email."
                
                return {
                    'success': True,
                    'response': response_text,
                    'type': 'email_classification',
                    'function_used': 'classify_email'
                }
            
            elif function_name == 'search_emails':
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
            
            elif function_name == 'get_recent_emails':
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
            
            elif function_name == 'retrieve_email_content':
                if result_data.get('success'):
                    email_content = result_data.get('email_content', '')
                    metadata = result_data.get('metadata', {})
                    query = result_data.get('query', '')
                    
                    # Provide the email content for further processing
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
            
            elif function_name == 'search_threads':
                threads = result_data.get('threads', [])
                count = result_data.get('count', 0)
                
                if count > 0:
                    response_text = f"🧵 **Conversations trouvées:** {count} conversation(s)\n\n"
                    for i, thread in enumerate(threads[:5], 1):
                        subject = thread.get('subject', 'Sans sujet')
                        participants = thread.get('participants', [])
                        message_count = thread.get('message_count', 0)
                        has_unread = thread.get('has_unread', False)
                        
                        unread_indicator = "🔴 " if has_unread else ""
                        response_text += f"{i}. {unread_indicator}**{subject}** ({message_count} messages)\n"
                        if participants:
                            response_text += f"   Participants: {', '.join(participants[:3])}\n"
                else:
                    response_text = "🧵 Aucune conversation trouvée pour cette recherche."
                
                return {
                    'success': True,
                    'response': response_text,
                    'type': 'thread_search',
                    'function_used': 'search_threads'
                }
            
            elif function_name == 'get_unread_emails':
                emails = result_data.get('emails', [])
                count = result_data.get('count', 0)
                
                if count > 0:
                    response_text = f"🔴 **Emails non lus:** {count} email(s)\n\n"
                    for i, email in enumerate(emails[:5], 1):
                        subject = email.get('subject', 'Sans sujet')
                        sender = email.get('sender_name', 'Expéditeur inconnu')
                        response_text += f"{i}. **{subject}** (de {sender})\n"
                else:
                    response_text = "✅ Aucun email non lu ! Vous êtes à jour."
                
                return {
                    'success': True,
                    'response': response_text,
                    'type': 'unread_emails',
                    'function_used': 'get_unread_emails'
                }
            
            elif function_name == 'get_user_mailboxes':
                mailboxes = result_data.get('mailboxes', [])
                count = result_data.get('count', 0)
                
                if count > 0:
                    response_text = f"📮 **Vos boîtes mail:** {count} boîte(s) accessible(s)\n\n"
                    for i, mailbox in enumerate(mailboxes, 1):
                        email = mailbox.get('email', 'Email inconnu')
                        contact_name = mailbox.get('contact_name')
                        name_part = f" ({contact_name})" if contact_name else ""
                        response_text += f"{i}. **{email}**{name_part}\n"
                else:
                    response_text = "❌ Aucune boîte mail accessible trouvée."
                
                return {
                    'success': True,
                    'response': response_text,
                    'type': 'user_mailboxes',
                    'function_used': 'get_user_mailboxes'
                }
            
            elif function_name == 'get_thread_statistics':
                stats = result_data
                
                if stats:
                    total = stats.get('total_threads', 0)
                    unread = stats.get('unread_threads', 0)
                    starred = stats.get('starred_threads', 0)
                    drafts = stats.get('draft_threads', 0)
                    trashed = stats.get('trashed_threads', 0)
                    spam = stats.get('spam_threads', 0)
                    
                    response_text = f"📊 **Statistiques de vos conversations:**\n\n"
                    response_text += f"• **Total:** {total} conversations\n"
                    response_text += f"• **Non lues:** {unread} conversations\n"
                    response_text += f"• **Favorites:** {starred} conversations\n"
                    response_text += f"• **Brouillons:** {drafts} conversations\n"
                    response_text += f"• **Corbeille:** {trashed} conversations\n"
                    response_text += f"• **Spam:** {spam} conversations\n"
                else:
                    response_text = "📊 Aucune statistique disponible."
                
                return {
                    'success': True,
                    'response': response_text,
                    'type': 'thread_statistics',
                    'function_used': 'get_thread_statistics'
                }
            
            elif function_name == 'create_draft_email':
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
            
            elif function_name == 'send_email':
                if result_data.get('success'):
                    subject = result_data.get('subject', 'Sans sujet')
                    sent_at = result_data.get('sent_at', '')
                    message_id = result_data.get('message_id', '')
                    
                    response_text = f"✅ **Email envoyé avec succès !**\n\n"
                    response_text += f"**Sujet:** {subject}\n"
                    response_text += f"**Envoyé le:** {sent_at}\n"
                    response_text += f"**ID du message:** {message_id}"
                else:
                    error_msg = result_data.get('error', 'Erreur inconnue')
                    response_text = f"❌ **Erreur lors de l'envoi de l'email:**\n\n{error_msg}"
                
                return {
                    'success': result_data.get('success', False),
                    'response': response_text,
                    'type': 'email_sent',
                    'function_used': 'send_email'
                }
            
            elif function_name == 'reply_to_email':
                if result_data.get('success'):
                    subject = result_data.get('subject', 'Sans sujet')
                    is_draft = result_data.get('is_draft', False)
                    message_id = result_data.get('message_id', '')
                    
                    if is_draft:
                        response_text = f"📝 **Brouillon de réponse créé !**\n\n"
                        response_text += f"**Sujet:** {subject}\n"
                        response_text += f"**ID du brouillon:** {message_id}\n\n"
                        response_text += "Le brouillon de réponse a été sauvegardé."
                    else:
                        sent_at = result_data.get('sent_at', '')
                        response_text = f"↩️ **Réponse envoyée avec succès !**\n\n"
                        response_text += f"**Sujet:** {subject}\n"
                        response_text += f"**Envoyé le:** {sent_at}\n"
                        response_text += f"**ID du message:** {message_id}"
                else:
                    error_msg = result_data.get('error', 'Erreur inconnue')
                    response_text = f"❌ **Erreur lors de la réponse à l'email:**\n\n{error_msg}"
                
                return {
                    'success': result_data.get('success', False),
                    'response': response_text,
                    'type': 'email_reply_sent',
                    'function_used': 'reply_to_email'
                }
            
            elif function_name == 'forward_email':
                if result_data.get('success'):
                    subject = result_data.get('subject', 'Sans sujet')
                    is_draft = result_data.get('is_draft', False)
                    message_id = result_data.get('message_id', '')
                    recipients_count = result_data.get('recipients_count', 0)
                    
                    if is_draft:
                        response_text = f"📝 **Brouillon de transfert créé !**\n\n"
                        response_text += f"**Sujet:** {subject}\n"
                        response_text += f"**Destinataires:** {recipients_count} personne(s)\n"
                        response_text += f"**ID du brouillon:** {message_id}\n\n"
                        response_text += "Le brouillon de transfert a été sauvegardé."
                    else:
                        sent_at = result_data.get('sent_at', '')
                        response_text = f"↗️ **Email transféré avec succès !**\n\n"
                        response_text += f"**Sujet:** {subject}\n"
                        response_text += f"**Destinataires:** {recipients_count} personne(s)\n"
                        response_text += f"**Envoyé le:** {sent_at}\n"
                        response_text += f"**ID du message:** {message_id}"
                else:
                    error_msg = result_data.get('error', 'Erreur inconnue')
                    response_text = f"❌ **Erreur lors du transfert de l'email:**\n\n{error_msg}"
                
                return {
                    'success': result_data.get('success', False),
                    'response': response_text,
                    'type': 'email_forwarded',
                    'function_used': 'forward_email'
                }
            
                       
            
            elif function_name == 'delete_draft':
                if result_data.get('success'):
                    response_text = f"🗑️ **Brouillon supprimé avec succès !**\n\n"
                    response_text += result_data.get('message', 'Le brouillon a été supprimé.')
                else:
                    error_msg = result_data.get('error', 'Erreur inconnue')
                    response_text = f"❌ **Erreur lors de la suppression du brouillon:**\n\n{error_msg}"
                
                return {
                    'success': result_data.get('success', False),
                    'response': response_text,
                    'type': 'draft_deleted',
                    'function_used': 'delete_draft'
                }
            
            elif function_name == 'reply_chain':
                # Handle the chained reply operation (retrieve → generate_reply → create_draft)
                # Check success at the function_result level, not result_data level
                is_successful = function_result.get('success', False)
                
                if is_successful:
                    reply_content = result_data.get('reply_content', '')
                    draft_subject = result_data.get('draft_subject', 'Sans sujet')
                    recipients = result_data.get('recipients', [])
                    draft_created = result_data.get('draft_created', {})
                    message_id = draft_created.get('message_id', '')
                    
                    recipient_names = [r.get('name', r.get('email', 'Destinataire')) for r in recipients]
                    
                    response_text = f"✅ **Réponse générée et brouillon créé avec succès !**\n\n"
                    response_text += f"**Sujet:** {draft_subject}\n"
                    response_text += f"**Destinataire(s):** {', '.join(recipient_names)}\n"
                    response_text += f"**ID du brouillon:** {message_id}\n\n"
                    response_text += f"**Contenu de la réponse générée:**\n"
                    response_text += f"```\n{reply_content[:500]}{'...' if len(reply_content) > 500 else ''}\n```\n\n"
                    response_text += "Le brouillon de réponse a été créé et est prêt à être envoyé.\n"
                    response_text += "Vous pouvez maintenant l'envoyer ou le modifier selon vos besoins."
                else:
                    error_msg = function_result.get('error', result_data.get('error', 'Erreur inconnue'))
                    response_text = f"❌ **Erreur lors de la génération de la réponse:**\n\n{error_msg}"
                
                return {
                    'success': is_successful,
                    'response': response_text,
                    'type': 'reply_chain_completed',
                    'function_used': 'reply_chain'
                }
            
            else:
                return {
                    'success': True,
                    'response': f"Fonction {function_name} exécutée avec succès.",
                    'type': 'function_result',
                    'function_used': function_name
                }
                
        except Exception as e:
            logger.error(f"Error formatting function response: {e}")
            return {
                'success': False,
                'response': f"Erreur lors du formatage de la réponse pour {function_name}.",
                'type': 'error',
                'function_used': function_name
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

    def _handle_multi_step_functions(self, user_message: str, user_id: str = None, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Mini Function-Calling Controller (mini-MCP)
        
        Implements a flexible function calling loop that:
        - Lets the model choose which function(s) to call dynamically
        - Handles multi-turn, multi-tool conversations
        - Does not rely on predefined workflows
        - Supports multiple sequential or parallel tool calls
        
        Args:
            user_message: The user's input message
            user_id: User ID for email operations
            conversation_history: Previous conversation messages
            
        Returns:
            Dictionary containing the final response after function calls, or None if not applicable
        """
        try:
            logger.info("Starting mini-MCP function calling controller")
            
            # Dynamic system prompt that lets the model decide everything
            dynamic_prompt = """
            Tu es un assistant intelligent avec accès à des outils de gestion d'emails. Tu peux analyser la demande de l'utilisateur et décider quels outils utiliser, dans quel ordre, et combien d'étapes sont nécessaires.

            🎯 APPROCHE DYNAMIQUE:
            - Analyse la demande de l'utilisateur
            - Décide quels outils utiliser et dans quel ordre
            - Tu peux faire plusieurs appels d'outils en séquence ou en parallèle
            - Utilise les résultats d'un outil comme entrée pour le suivant si nécessaire
            - Sois créatif et flexible dans ton approche

            🔧 OUTILS DISPONIBLES:
            - retrieve_email_content: Récupère le contenu d'un email spécifique
            - search_emails: Recherche des emails par mots-clés
            - get_recent_emails: Récupère les emails récents
            - get_unread_emails: Récupère les emails non lus
            - summarize_email: Résume un email
            - classify_email: Classifie un email
            - generate_email_reply: Génère une réponse à un email
            - create_draft_email: Crée un brouillon d'email
            - send_email: Envoie un email
            - reply_to_email: Répond directement à un email
            - forward_email: Transfère un email
            - get_user_mailboxes: Liste les boîtes mails accessibles
            - get_thread_statistics: Statistiques des conversations
            - search_threads: Recherche des conversations
            - delete_draft: Supprime un brouillon

            🚀 STRATÉGIES POSSIBLES:
            - Pour "résume l'email de X": retrieve_email_content → summarize_email
            - Pour "réponds à l'email de Y": retrieve_email_content → generate_email_reply → create_draft_email
            - Pour "trouve et résume les emails urgents": search_emails → summarize_email (pour chaque)
            - Pour "classifie mes emails récents": get_recent_emails → classify_email (pour chaque)
            - Pour des demandes complexes: combine plusieurs outils créativement

            ✨ RÈGLES:
            - Tu décides complètement de la stratégie à adopter
            - Tu peux utiliser autant d'outils que nécessaire
            - Sois intelligent sur l'ordre des opérations
            - Utilise le contexte des résultats précédents
            - Si une demande semble nécessiter des outils, utilise-les
            - Si c'est une conversation générale, réponds normalement

            Analyse la demande et agis en conséquence.
            """
            
            # Initialize conversation history
            if conversation_history is None:
                conversation_history = []
            
            # Build the conversation with dynamic guidance
            messages = [{"role": "system", "content": dynamic_prompt}]
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_message})
            
            # Get available tools
            tools = self._get_email_tools()
            logger.info(f"Available tools for mini-MCP: {len(tools)} tools")
            
            # Start the function calling loop
            max_iterations = 5  # Prevent infinite loops
            iteration = 0
            all_results = []
            conversation_context = ""
            
            while iteration < max_iterations:
                iteration += 1
                logger.info(f"🔄 Mini-MCP iteration {iteration}/{max_iterations}")
                
                # Add accumulated context to the conversation if we have previous results
                current_messages = messages.copy()
                if conversation_context:
                    logger.info(f"📝 Adding accumulated context to iteration {iteration} ({len(conversation_context)} chars)")
                    logger.debug(f"📝 Context being added: {conversation_context[:300]}...")
                    
                    current_messages.append({
                        "role": "assistant", 
                        "content": f"Contexte des outils précédents:\n{conversation_context}"
                    })
                    current_messages.append({
                        "role": "user", 
                        "content": "Continue avec les outils suivants si nécessaire, ou fournis la réponse finale."
                    })
                else:
                    logger.info(f"📝 No accumulated context for iteration {iteration} (first iteration)")
                
                logger.info(f"🤖 Making request to Albert API for iteration {iteration} with {len(current_messages)} messages")
                
                # Make request to get the model's decision
                response = self._make_request(current_messages, tools)
                choice = response.get('choices', [{}])[0]
                message = choice.get('message', {})
                
                # Check if the model wants to use tools
                tool_calls_made = False
                
                if 'tool_calls' in message and message['tool_calls']:
                    tool_calls_made = True
                    logger.info(f"Model wants to call {len(message['tool_calls'])} tool(s) in iteration {iteration}")
                    
                    # Execute all tool calls in this iteration
                    iteration_results = []
                    for j, tool_call in enumerate(message['tool_calls']):
                        if tool_call['type'] == 'function':
                            function_name = tool_call['function']['name']
                            raw_arguments = tool_call['function']['arguments']
                            
                            logger.info(f"Iteration {iteration}, Tool {j+1}: Parsing tool call for {function_name}")
                            logger.debug(f"Raw function arguments received: {raw_arguments}")
                            
                            try:
                                function_args = json.loads(raw_arguments)
                                logger.info(f"Successfully parsed arguments for {function_name}: {function_args}")
                                logger.debug(f"Argument types: {[(k, type(v).__name__) for k, v in function_args.items()]}")
                            except json.JSONDecodeError as e:
                                logger.error(f"Invalid JSON in function arguments for {function_name}: {e}")
                                logger.error(f"Failed to parse raw arguments: {raw_arguments}")
                                continue
                            
                            logger.info(f"Iteration {iteration}, Tool {j+1}: Executing {function_name} with {len(function_args)} argument(s)")
                            logger.info(f"🔧 Function: {function_name}")
                            logger.info(f"📋 Arguments Summary:")
                            for key, value in function_args.items():
                                if isinstance(value, str) and len(value) > 100:
                                    logger.info(f"  - {key}: '{value[:100]}...' ({len(value)} chars)")
                                elif isinstance(value, (list, dict)):
                                    logger.info(f"  - {key}: {type(value).__name__} with {len(value)} items")
                                else:
                                    logger.info(f"  - {key}: {value}")
                            
                            # Execute the function
                            function_result = self._execute_email_function(function_name, function_args, user_id)
                            
                            logger.info(f"🎯 Function execution completed - {function_name}: success={function_result.get('success')}")
                            if function_result.get('success'):
                                logger.info(f"✅ {function_name} executed successfully")
                                if 'execution_time' in function_result:
                                    logger.info(f"⏱️ Execution time: {function_result['execution_time']:.2f}s")
                            else:
                                logger.warning(f"❌ {function_name} failed: {function_result.get('error', 'Unknown error')}")
                                if 'execution_time' in function_result:
                                    logger.warning(f"⏱️ Failed after: {function_result['execution_time']:.2f}s")
                            if not function_result.get('success'):
                                logger.warning(f"⚠️ Function {function_name} failed: {function_result.get('error', 'No error message')}")
                            
                            step_result = {
                                'iteration': iteration,
                                'step': len(all_results) + 1,
                                'function': function_name,
                                'args': function_args,
                                'result': function_result,
                                'success': function_result.get('success', False)
                            }
                            
                            logger.debug(f"📊 Step result created: step {step_result['step']}, function: {function_name}, success: {step_result['success']}")
                            
                            iteration_results.append(step_result)
                            all_results.append(step_result)
                            
                            # Build context for next iteration
                            if function_result.get('success'):
                                result_summary = self._summarize_function_result(function_name, function_result)
                                conversation_context += f"\n\n✅ {function_name}: {result_summary}"
                                logger.info(f"✅ Added success context: {result_summary}")
                            else:
                                error_msg = function_result.get('error', 'Erreur inconnue')
                                conversation_context += f"\n\n❌ {function_name}: Échec - {error_msg}"
                                logger.warning(f"❌ Added error context: {error_msg}")
                                logger.warning(f"Function {function_name} failed: {error_msg}")
                    
                    logger.info(f"🔄 Completed iteration {iteration} with {len(iteration_results)} tool calls")
                    logger.debug(f"📝 Current conversation context length: {len(conversation_context)} characters")
                    logger.debug(f"📊 Total results so far: {len(all_results)} steps")
                    
                    # Log summary of this iteration
                    successful_in_iteration = sum(1 for r in iteration_results if r.get('success', False))
                    logger.info(f"📈 Iteration {iteration} summary: {successful_in_iteration}/{len(iteration_results)} successful tool calls")
                
                # Check for legacy function_call format
                elif 'function_call' in message:
                    tool_calls_made = True
                    function_call = message['function_call']
                    function_name = function_call['name']
                    
                    logger.info(f"📞 Legacy function call in iteration {iteration}: {function_name}")
                    logger.debug(f"Raw legacy function arguments: {function_call['arguments']}")
                    
                    try:
                        function_args = json.loads(function_call['arguments'])
                        logger.info(f"✅ Successfully parsed legacy function arguments: {function_args}")
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Invalid JSON in legacy function arguments: {e}")
                        logger.error(f"Failed to parse: {function_call['arguments']}")
                        break
                    
                    # Log argument details
                    logger.info(f"🔧 Legacy Function: {function_name}")
                    logger.info(f"📋 Legacy Arguments Summary:")
                    for key, value in function_args.items():
                        if isinstance(value, str) and len(value) > 100:
                            logger.info(f"  - {key}: '{value[:100]}...' ({len(value)} chars)")
                        elif isinstance(value, (list, dict)):
                            logger.info(f"  - {key}: {type(value).__name__} with {len(value)} items")
                        else:
                            logger.info(f"  - {key}: {value}")
                    
                    function_result = self._execute_email_function(function_name, function_args, user_id)
                    
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
                
                # If no tools were called, the model is done
                if not tool_calls_made:
                    logger.info(f"🏁 No more tools called in iteration {iteration}. Mini-MCP complete.")
                    logger.info(f"📊 Final summary: {len(all_results)} total steps executed")
                    
                    # Check if we have any results to format
                    if all_results:
                        # Get the final response content from the model
                        final_content = message.get('content', '').strip()
                        logger.info(f"💬 Final model content length: {len(final_content)} characters")
                        logger.debug(f"💬 Final model content preview: {final_content[:200]}...")
                        
                        logger.info("🎨 Formatting final mini-MCP response")
                        return self._format_mini_mcp_response(all_results, user_message, final_content)
                    else:
                        # No tools were used, this wasn't a function calling request
                        logger.info("🚫 No tools were used, not a function calling request")
                        return None
            
            # If we reached max iterations, format response with what we have
            if all_results:
                logger.warning(f"Mini-MCP reached max iterations ({max_iterations})")
                return self._format_mini_mcp_response(all_results, user_message, "Traitement terminé après plusieurs étapes.")
            
            # No function calls were made
            return None
            
        except Exception as e:
            logger.error(f"Error in mini-MCP function calling controller: {e}", exc_info=True)
            return None
            
    def _summarize_function_result(self, function_name: str, function_result: Dict[str, Any]) -> str:
        """
        Create a concise summary of a function result for context building.
        
        Args:
            function_name: Name of the function that was executed
            function_result: Result from the function execution
            
        Returns:
            Concise summary string
        """
        try:
            result_data = function_result.get('result', {})
            
            if function_name == 'retrieve_email_content':
                if result_data.get('success'):
                    metadata = result_data.get('metadata', {})
                    subject = metadata.get('subject', 'Sans sujet')
                    sender = metadata.get('sender_name', 'Expéditeur inconnu')
                    return f"Email récupéré: '{subject}' de {sender}"
                else:
                    return "Échec de récupération d'email"
            
            elif function_name == 'search_emails':
                count = result_data.get('count', 0)
                return f"{count} email(s) trouvé(s)"
            
            elif function_name == 'get_recent_emails':
                count = result_data.get('count', 0)
                return f"{count} email(s) récent(s) récupéré(s)"
            
            elif function_name == 'get_unread_emails':
                count = result_data.get('count', 0)
                return f"{count} email(s) non lu(s)"
            
            elif function_name == 'summarize_email':
                if result_data.get('success'):
                    return "Email résumé avec succès"
                else:
                    return "Échec du résumé"
            
            elif function_name == 'classify_email':
                if result_data.get('success'):
                    classification = result_data.get('classification', {})
                    category = classification.get('primary_category', 'inconnu')
                    return f"Email classifié comme: {category}"
                else:
                    return "Échec de classification"
            
            elif function_name == 'generate_email_reply':
                if result_data.get('success'):
                    return "Réponse générée avec succès"
                else:
                    return "Échec de génération de réponse"
            
            elif function_name == 'create_draft_email':
                if result_data.get('success'):
                    return "Brouillon créé avec succès"
                else:
                    return "Échec de création de brouillon"
            
            elif function_name == 'send_email':
                if result_data.get('success'):
                    return "Email envoyé avec succès"
                else:
                    return "Échec d'envoi d'email"
            
            else:
                # Generic summary for other functions
                if function_result.get('success'):
                    return f"{function_name} exécuté avec succès"
                else:
                    return f"Échec de {function_name}"
                    
        except Exception as e:
            logger.error(f"Error summarizing function result: {e}")
            return f"{function_name} - résumé indisponible"

    def _format_mini_mcp_response(self, all_results: List[Dict], original_message: str, final_content: str = "") -> Dict[str, Any]:
        """
        Format the final response from the mini-MCP controller.
        
        Args:
            all_results: List of all function execution results
            original_message: Original user message
            final_content: Final content from the model
            
        Returns:
            Formatted response dictionary
        """
        try:
            if not all_results:
                return {
                    'success': False,
                    'response': 'Aucune action n\'a pu être effectuée.',
                    'type': 'mini_mcp_error'
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
                
                # Get detailed content for key functions
                if function_name == 'summarize_email':
                    result_data = function_result.get('result', {})
                    if result_data.get('success'):
                        summary_data = result_data.get('summary', {})
                        if isinstance(summary_data, dict):
                            summary_text = summary_data.get('summary', '')
                            if summary_text:
                                response_parts.append(f"\n📋 **Résumé:**\n{summary_text}")
                        else:
                            response_parts.append(f"\n📋 **Résumé:**\n{str(summary_data)}")
                
                elif function_name == 'generate_email_reply':
                    result_data = function_result.get('result', {})
                    if result_data.get('success'):
                        response_data = result_data.get('response', {})
                        if isinstance(response_data, dict):
                            reply_text = response_data.get('response', '')
                            if reply_text:
                                response_parts.append(f"\n✉️ **Réponse générée:**\n{reply_text}")
                        else:
                            response_parts.append(f"\n✉️ **Réponse générée:**\n{str(response_data)}")
                
                elif function_name == 'classify_email':
                    result_data = function_result.get('result', {})
                    if result_data.get('success'):
                        classification = result_data.get('classification', {})
                        category = classification.get('primary_category', 'Non classé')
                        confidence = classification.get('confidence_score', 0)
                        reasoning = classification.get('reasoning', '')
                        response_parts.append(f"\n🏷️ **Classification:**\n**Catégorie:** {category}\n**Confiance:** {confidence:.2f}\n**Justification:** {reasoning}")
                
                elif function_name == 'create_draft_email':
                    result_data = function_result.get('result', {})
                    if result_data.get('success'):
                        subject = result_data.get('subject', 'Sans sujet')
                        message_id = result_data.get('message_id', '')
                        response_parts.append(f"\n📝 **Brouillon créé:**\n**Sujet:** {subject}\n**ID:** {message_id}")
            
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
                'type': 'mini_mcp_completed',
                'steps_total': total_steps,
                'steps_successful': success_count,
                'steps_failed': len(failed_steps),
                'all_results': all_results,
                'final_function': successful_steps[-1]['function'] if successful_steps else None
            }
            
        except Exception as e:
            logger.error(f"Error formatting mini-MCP response: {e}", exc_info=True)
            return {
                'success': False,
                'response': f"Erreur lors du formatage de la réponse: {str(e)}",
                'type': 'mini_mcp_error'
            }

def get_chatbot(config: Optional[AlbertConfig] = None) -> AlbertChatbot:
    """
    Factory function to get a configured AlbertChatbot instance.
    
    Args:
        config: Optional configuration for Albert API. If None, uses default config.
        
    Returns:
        Configured AlbertChatbot instance
    """
    return AlbertChatbot(config=config)


