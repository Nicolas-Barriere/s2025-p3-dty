"""
Email processing operations using Albert API.

This module provides core email processing functionality like summarization,
classification, and response generation.
"""

import json
import logging
from typing import Dict, List, Optional, Any

from .api_client import AlbertAPIClient
from .config import MailClassification
from .parsers import ContentParser
from .exceptions import AlbertAPIError

logger = logging.getLogger(__name__)


class EmailProcessor:
    """Handles email processing operations using Albert API."""
    
    def __init__(self, api_client: AlbertAPIClient):
        """
        Initialize the email processor.
        
        Args:
            api_client: Albert API client instance
        """
        self.api_client = api_client
        self.parser = ContentParser()
    
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
            
            response = self.api_client.make_request(messages, functions)
            
            # Extract function call result or content response
            return self._process_response(response, 'summary', sender, subject)
            
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
            
            response = self.api_client.make_request(messages, functions)
            
            return self._process_response(response, 'answer', context, tone)
            
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
            
            response = self.api_client.make_request(messages, functions)
            
            return self._process_response(response, 'classification', categories, sender, subject)
            
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
    
    def validate_email_content(self, mail_content: str, sender: str = "", subject: str = "") -> Dict[str, Any]:
        """
        Validate email content before processing.
        
        Args:
            mail_content: The email content to validate
            sender: Email sender (optional)
            subject: Email subject (optional)
            
        Returns:
            Dictionary containing validation results
        """
        validation_result = {
            'is_valid': True,
            'warnings': [],
            'errors': []
        }
        
        # Check content length
        if not mail_content or len(mail_content.strip()) < 10:
            validation_result['errors'].append("Le contenu de l'email est trop court ou vide")
            validation_result['is_valid'] = False
        
        if len(mail_content) > 50000:  # 50KB limit
            validation_result['warnings'].append("Le contenu de l'email est très long, cela pourrait affecter les performances")
        
        # Check for suspicious content
        suspicious_keywords = ['spam', 'phishing', 'malware', 'virus']
        content_lower = mail_content.lower()
        for keyword in suspicious_keywords:
            if keyword in content_lower:
                validation_result['warnings'].append(f"Contenu potentiellement suspect détecté: {keyword}")
        
        # Check sender format if provided
        if sender and '@' not in sender and len(sender) > 0:
            validation_result['warnings'].append("Format d'expéditeur potentiellement invalide")
        
        logger.info(f"Email validation - Valid: {validation_result['is_valid']}, "
                   f"Warnings: {len(validation_result['warnings'])}, "
                   f"Errors: {len(validation_result['errors'])}")
        
        return validation_result
    
    def analyze_email_sentiment(self, mail_content: str, sender: str = "", subject: str = "") -> Dict[str, Any]:
        """
        Analyze the sentiment and emotional tone of an email.
        
        Args:
            mail_content: The content of the email to analyze
            sender: Email sender (optional)
            subject: Email subject (optional)
            
        Returns:
            Dictionary containing sentiment analysis results
        """
        try:
            logger.info(f"Analyzing email sentiment from sender: {sender}")
            
            mail_context = f"""
            Expéditeur: {sender}
            Sujet: {subject}
            Contenu: {mail_content}
            """
            
            functions = [{
                "name": "analyze_email_sentiment",
                "description": "Analyse le sentiment et le ton émotionnel d'un email",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sentiment": {
                            "type": "string",
                            "enum": ["positive", "negative", "neutral"],
                            "description": "Sentiment général de l'email"
                        },
                        "emotional_tone": {
                            "type": "string",
                            "enum": ["professional", "friendly", "angry", "urgent", "disappointed", "grateful", "concerned"],
                            "description": "Ton émotionnel de l'email"
                        },
                        "confidence_score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Score de confiance de l'analyse"
                        },
                        "key_emotions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Émotions clés détectées"
                        },
                        "response_suggestion": {
                            "type": "string",
                            "description": "Suggestion de ton pour la réponse"
                        }
                    },
                    "required": ["sentiment", "emotional_tone", "confidence_score"]
                }
            }]
            
            system_prompt = """
            Tu es un expert en analyse de sentiment et de ton émotionnel dans les communications écrites.
            Tu DOIS utiliser la fonction analyze_email_sentiment pour analyser le sentiment des emails.
            
            Analyse le sentiment général, le ton émotionnel et les émotions clés présentes dans l'email.
            Fournis également une suggestion de ton approprié pour répondre.
            """
            
            user_prompt = f"""
            Utilise la fonction analyze_email_sentiment pour analyser le sentiment de cet email:
            
            {mail_context}
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.api_client.make_request(messages, functions)
            
            return self._process_response(response, 'sentiment', sender, subject)
            
        except Exception as e:
            logger.error(f"Error analyzing email sentiment: {e}")
            return {
                'success': False,
                'error': str(e),
                'sentiment_analysis': {
                    'sentiment': 'neutral',
                    'emotional_tone': 'professional',
                    'confidence_score': 0.0,
                    'key_emotions': [],
                    'response_suggestion': 'professional'
                }
            }
    
    def extract_email_entities(self, mail_content: str, sender: str = "", subject: str = "") -> Dict[str, Any]:
        """
        Extract key entities (dates, names, organizations, etc.) from an email.
        
        Args:
            mail_content: The content of the email to analyze
            sender: Email sender (optional)
            subject: Email subject (optional)
            
        Returns:
            Dictionary containing extracted entities
        """
        try:
            logger.info(f"Extracting entities from email from sender: {sender}")
            
            mail_context = f"""
            Expéditeur: {sender}
            Sujet: {subject}
            Contenu: {mail_content}
            """
            
            functions = [{
                "name": "extract_email_entities",
                "description": "Extrait les entités clés d'un email (dates, noms, organisations, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "persons": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Noms de personnes mentionnées"
                        },
                        "organizations": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Organisations ou entreprises mentionnées"
                        },
                        "dates": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Dates mentionnées dans l'email"
                        },
                        "locations": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Lieux mentionnés"
                        },
                        "amounts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Montants ou prix mentionnés"
                        },
                        "phone_numbers": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Numéros de téléphone trouvés"
                        },
                        "email_addresses": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Adresses email mentionnées"
                        },
                        "urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "URLs ou liens mentionnés"
                        }
                    },
                    "required": ["persons", "organizations", "dates", "locations"]
                }
            }]
            
            system_prompt = """
            Tu es un expert en extraction d'entités nommées à partir de textes.
            Tu DOIS utiliser la fonction extract_email_entities pour extraire les entités importantes des emails.
            
            Identifie et extrait tous les noms de personnes, organisations, dates, lieux, montants,
            numéros de téléphone, adresses email et URLs mentionnés dans l'email.
            """
            
            user_prompt = f"""
            Utilise la fonction extract_email_entities pour extraire les entités de cet email:
            
            {mail_context}
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.api_client.make_request(messages, functions)
            
            return self._process_response(response, 'entities', sender, subject)
            
        except Exception as e:
            logger.error(f"Error extracting email entities: {e}")
            return {
                'success': False,
                'error': str(e),
                'entities': {
                    'persons': [],
                    'organizations': [],
                    'dates': [],
                    'locations': [],
                    'amounts': [],
                    'phone_numbers': [],
                    'email_addresses': [],
                    'urls': []
                }
            }
    
    def generate_email_metadata(self, mail_content: str, sender: str = "", subject: str = "") -> Dict[str, Any]:
        """
        Generate comprehensive metadata for an email.
        
        Args:
            mail_content: The content of the email
            sender: Email sender (optional)
            subject: Email subject (optional)
            
        Returns:
            Dictionary containing comprehensive email metadata
        """
        try:
            # Perform validation
            validation = self.validate_email_content(mail_content, sender, subject)
            
            # Basic metadata
            metadata = {
                'content_length': len(mail_content),
                'word_count': len(mail_content.split()),
                'paragraph_count': len([p for p in mail_content.split('\n\n') if p.strip()]),
                'line_count': len(mail_content.split('\n')),
                'validation': validation
            }
            
            # Enhanced content analysis
            content_analysis = self._enhance_content_analysis(mail_content, 'metadata')
            metadata.update(content_analysis)
            
            # Detect patterns
            patterns = {
                'has_greeting': any(greet in mail_content.lower() for greet in ['bonjour', 'salut', 'hello', 'bonsoir']),
                'has_signature': any(sig in mail_content.lower() for sig in ['cordialement', 'salutations', 'bien à vous']),
                'has_attachments_mention': any(att in mail_content.lower() for att in ['pièce jointe', 'fichier joint', 'attachment']),
                'has_meeting_mention': any(meet in mail_content.lower() for meet in ['réunion', 'rendez-vous', 'meeting', 'rdv']),
                'has_deadline_mention': any(dead in mail_content.lower() for dead in ['urgent', 'deadline', 'échéance', 'délai']),
                'has_question': '?' in mail_content,
                'has_exclamation': '!' in mail_content
            }
            metadata['patterns'] = patterns
            
            # Language indicators
            french_indicators = ['le', 'la', 'les', 'de', 'du', 'des', 'et', 'ou', 'dans', 'avec']
            english_indicators = ['the', 'and', 'or', 'in', 'with', 'for', 'to', 'of', 'a', 'an']
            
            content_lower = mail_content.lower()
            french_count = sum(1 for indicator in french_indicators if indicator in content_lower)
            english_count = sum(1 for indicator in english_indicators if indicator in content_lower)
            
            if french_count > english_count:
                metadata['detected_language'] = 'french'
            elif english_count > french_count:
                metadata['detected_language'] = 'english'
            else:
                metadata['detected_language'] = 'unknown'
            
            metadata['language_confidence'] = max(french_count, english_count) / max(len(mail_content.split()), 1)
            
            logger.info(f"Generated metadata for email from {sender}: {metadata['word_count']} words, {metadata['detected_language']} language")
            
            return {
                'success': True,
                'metadata': metadata,
                'original_sender': sender,
                'original_subject': subject
            }
            
        except Exception as e:
            logger.error(f"Error generating email metadata: {e}")
            return {
                'success': False,
                'error': str(e),
                'metadata': {}
            }
    
    def _process_response(self, response: Dict[str, Any], operation_type: str, *args) -> Dict[str, Any]:
        """
        Process Albert API response and extract function call results or content.
        
        Args:
            response: Raw response from Albert API
            operation_type: Type of operation ('summary', 'answer', 'classification')
            *args: Additional arguments specific to the operation
            
        Returns:
            Processed response dictionary
        """
        try:
            # Validate response structure
            if not response or 'choices' not in response:
                logger.error(f"Invalid response structure for {operation_type}")
                return self._format_error_response(operation_type, 'Structure de réponse invalide de l\'API Albert')
            
            choices = response.get('choices', [])
            if not choices:
                logger.error(f"No choices in response for {operation_type}")
                return self._format_error_response(operation_type, 'Aucun choix dans la réponse de l\'API Albert')
            
            choice = choices[0]
            message = choice.get('message', {})
            
            # Check for new tool_calls format first
            if 'tool_calls' in message and message['tool_calls']:
                tool_call = message['tool_calls'][0]
                if tool_call['type'] == 'function':
                    function_call = tool_call['function']
                    function_name = function_call.get('name', '')
                    
                    # Validate function name matches expected operation
                    expected_functions = {
                        'summary': 'summarize_email',
                        'answer': 'generate_email_response', 
                        'classification': 'classify_email',
                        'sentiment': 'analyze_email_sentiment',
                        'entities': 'extract_email_entities'
                    }
                    
                    if function_name == expected_functions.get(operation_type):
                        try:
                            function_data = json.loads(function_call['arguments'])
                            logger.info(f"Successfully processed {operation_type} using function call: {function_name}")
                            
                            # Validate function data structure
                            validation_result = self._validate_function_data(operation_type, function_data)
                            if not validation_result['is_valid']:
                                logger.warning(f"Function data validation warnings for {operation_type}: {validation_result['warnings']}")
                            
                            return self._format_success_response(operation_type, function_data, *args)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse function arguments for {function_name}: {e}")
                            # Fall through to content processing
                        except Exception as e:
                            logger.error(f"Error processing function call {function_name}: {e}")
                            # Fall through to content processing
            
            # Check for legacy function_call format
            elif 'function_call' in message:
                function_call = message['function_call']
                function_name = function_call.get('name', '')
                
                try:
                    function_data = json.loads(function_call['arguments'])
                    logger.info(f"Successfully processed {operation_type} using legacy function call: {function_name}")
                    
                    # Validate function data structure
                    validation_result = self._validate_function_data(operation_type, function_data)
                    if not validation_result['is_valid']:
                        logger.warning(f"Function data validation warnings for {operation_type}: {validation_result['warnings']}")
                    
                    return self._format_success_response(operation_type, function_data, *args)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse legacy function arguments for {function_name}: {e}")
                    # Fall through to content processing
                except Exception as e:
                    logger.error(f"Error processing legacy function call {function_name}: {e}")
                    # Fall through to content processing
            
            # Albert API uses content-based responses (which are excellent)
            content = message.get('content', '')
            if content:
                content = content.strip()
                if len(content) > 0:
                    logger.info(f"Successfully processed {operation_type} using content response")
                    logger.debug(f"Content length: {len(content)} characters")
                    
                    # Enhanced content processing
                    parsed_data = self._parse_content_response(operation_type, content, *args)
                    
                    # Validate parsed data
                    validation_result = self._validate_function_data(operation_type, parsed_data)
                    if not validation_result['is_valid']:
                        logger.warning(f"Parsed content validation warnings for {operation_type}: {validation_result['warnings']}")
                    
                    return self._format_success_response(operation_type, parsed_data, *args)
            
            # No content at all
            logger.error(f"No content received from Albert API for {operation_type}")
            return self._format_error_response(operation_type, 'Aucune réponse reçue de l\'API Albert')
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse function arguments for {operation_type}: {e}")
            return self._format_error_response(operation_type, f'Erreur de parsing JSON: {str(e)}')
        except Exception as e:
            logger.error(f"Error processing response for {operation_type}: {e}")
            logger.error(f"Response structure: {response}")
            return self._format_error_response(operation_type, str(e))
    
    def _parse_content_response(self, operation_type: str, content: str, *args) -> Dict[str, Any]:
        """Parse content response based on operation type with enhanced analysis."""
        # Perform enhanced content analysis
        content_analysis = self._enhance_content_analysis(content, operation_type)
        logger.debug(f"Content analysis for {operation_type}: {content_analysis}")
        
        # Parse based on operation type
        if operation_type == 'summary':
            parsed_data = self.parser.parse_summary_content(content)
            parsed_data['content_analysis'] = content_analysis
            return parsed_data
        elif operation_type == 'answer':
            tone = args[1] if len(args) > 1 else 'professional'
            parsed_data = self.parser.parse_answer_content(content, tone)
            parsed_data['content_analysis'] = content_analysis
            return parsed_data
        elif operation_type == 'classification':
            categories = args[0] if args else []
            parsed_data = self.parser.parse_classification_content(content, categories)
            parsed_data['content_analysis'] = content_analysis
            return parsed_data
        elif operation_type == 'sentiment':
            # For sentiment analysis, create a basic structure from content
            parsed_data = {
                'sentiment': 'neutral',
                'emotional_tone': 'professional',
                'confidence_score': 0.7,
                'key_emotions': [],
                'response_suggestion': 'professional',
                'raw_content': content
            }
            parsed_data['content_analysis'] = content_analysis
            return parsed_data
        elif operation_type == 'entities':
            # For entity extraction, create a basic structure from content
            parsed_data = {
                'persons': [],
                'organizations': [],
                'dates': [],
                'locations': [],
                'amounts': [],
                'phone_numbers': [],
                'email_addresses': [],
                'urls': [],
                'raw_content': content
            }
            parsed_data['content_analysis'] = content_analysis
            return parsed_data
        else:
            return {
                'content': content,
                'content_analysis': content_analysis
            }
    
    def _format_success_response(self, operation_type: str, data: Dict[str, Any], *args) -> Dict[str, Any]:
        """Format successful response based on operation type."""
        base_response = {'success': True}
        
        if operation_type == 'summary':
            sender, subject = args if len(args) >= 2 else ('', '')
            base_response.update({
                'summary': data,
                'original_sender': sender,
                'original_subject': subject
            })
        elif operation_type == 'answer':
            context, tone = args if len(args) >= 2 else ('', 'professional')
            base_response.update({
                'response': data,
                'context_used': context,
                'tone_requested': tone
            })
        elif operation_type == 'classification':
            categories = args[0] if args else []
            sender = args[1] if len(args) > 1 else ''
            subject = args[2] if len(args) > 2 else ''
            base_response.update({
                'classification': data,
                'available_categories': categories,
                'original_sender': sender,
                'original_subject': subject
            })
        elif operation_type == 'sentiment':
            sender, subject = args if len(args) >= 2 else ('', '')
            base_response.update({
                'sentiment_analysis': data,
                'original_sender': sender,
                'original_subject': subject
            })
        elif operation_type == 'entities':
            sender, subject = args if len(args) >= 2 else ('', '')
            base_response.update({
                'entities': data,
                'original_sender': sender,
                'original_subject': subject
            })
        else:
            # Generic response for unknown operation types
            base_response.update({
                'data': data,
                'operation_type': operation_type
            })
        
        return base_response
    
    def _format_error_response(self, operation_type: str, error_message: str) -> Dict[str, Any]:
        """Format error response based on operation type."""
        base_response = {'success': False, 'error': error_message}
        
        if operation_type == 'summary':
            base_response['summary'] = {'summary': 'Erreur lors du résumé de l\'email.'}
        elif operation_type == 'answer':
            base_response['response'] = {'response': 'Erreur lors de la génération de la réponse.'}
        elif operation_type == 'classification':
            base_response['classification'] = {
                'primary_category': 'normal',
                'confidence_score': 0.0,
                'reasoning': 'Erreur - aucune réponse de l\'API.'
            }
        elif operation_type == 'sentiment':
            base_response['sentiment_analysis'] = {
                'sentiment': 'neutral',
                'emotional_tone': 'professional',
                'confidence_score': 0.0,
                'key_emotions': [],
                'response_suggestion': 'professional'
            }
        elif operation_type == 'entities':
            base_response['entities'] = {
                'persons': [],
                'organizations': [],
                'dates': [],
                'locations': [],
                'amounts': [],
                'phone_numbers': [],
                'email_addresses': [],
                'urls': []
            }
        else:
            # Generic error response
            base_response['data'] = None
        
        return base_response
    
    def _validate_function_data(self, operation_type: str, function_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate function data structure and content.
        
        Args:
            operation_type: Type of operation being validated
            function_data: Data returned from function call
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'is_valid': True,
            'warnings': [],
            'errors': []
        }
        
        try:
            if operation_type == 'summary':
                # Validate summary structure
                if 'summary' not in function_data:
                    validation_result['errors'].append("Champ 'summary' manquant")
                    validation_result['is_valid'] = False
                elif not function_data['summary'] or len(function_data['summary'].strip()) < 10:
                    validation_result['warnings'].append("Résumé très court ou vide")
                
                if 'key_points' in function_data:
                    if not isinstance(function_data['key_points'], list):
                        validation_result['warnings'].append("Points clés ne sont pas dans une liste")
                    elif len(function_data['key_points']) == 0:
                        validation_result['warnings'].append("Aucun point clé fourni")
                
                if 'urgency_level' in function_data:
                    valid_levels = ['low', 'medium', 'high']
                    if function_data['urgency_level'] not in valid_levels:
                        validation_result['warnings'].append(f"Niveau d'urgence invalide: {function_data['urgency_level']}")
            
            elif operation_type == 'answer':
                # Validate answer structure
                if 'response' not in function_data:
                    validation_result['errors'].append("Champ 'response' manquant")
                    validation_result['is_valid'] = False
                elif not function_data['response'] or len(function_data['response'].strip()) < 20:
                    validation_result['warnings'].append("Réponse très courte")
                
                if 'subject' in function_data:
                    if not function_data['subject'] or len(function_data['subject'].strip()) < 3:
                        validation_result['warnings'].append("Sujet très court ou vide")
            
            elif operation_type == 'classification':
                # Validate classification structure
                if 'primary_category' not in function_data:
                    validation_result['errors'].append("Champ 'primary_category' manquant")
                    validation_result['is_valid'] = False
                
                if 'confidence_score' in function_data:
                    score = function_data['confidence_score']
                    if not isinstance(score, (int, float)) or score < 0 or score > 1:
                        validation_result['warnings'].append(f"Score de confiance invalide: {score}")
                
                if 'reasoning' not in function_data or not function_data['reasoning']:
                    validation_result['warnings'].append("Justification manquante ou vide")
            
            elif operation_type == 'sentiment':
                # Validate sentiment analysis structure
                if 'sentiment' not in function_data:
                    validation_result['errors'].append("Champ 'sentiment' manquant")
                    validation_result['is_valid'] = False
                elif function_data['sentiment'] not in ['positive', 'negative', 'neutral']:
                    validation_result['warnings'].append(f"Sentiment invalide: {function_data['sentiment']}")
                
                if 'emotional_tone' not in function_data:
                    validation_result['warnings'].append("Ton émotionnel manquant")
                
                if 'confidence_score' in function_data:
                    score = function_data['confidence_score']
                    if not isinstance(score, (int, float)) or score < 0 or score > 1:
                        validation_result['warnings'].append(f"Score de confiance invalide: {score}")
            
            elif operation_type == 'entities':
                # Validate entities extraction structure
                required_fields = ['persons', 'organizations', 'dates', 'locations']
                for field in required_fields:
                    if field not in function_data:
                        validation_result['warnings'].append(f"Champ '{field}' manquant")
                    elif not isinstance(function_data.get(field), list):
                        validation_result['warnings'].append(f"Champ '{field}' devrait être une liste")
                
                # Check for reasonable entity counts
                total_entities = sum(len(function_data.get(field, [])) for field in required_fields)
                if total_entities == 0:
                    validation_result['warnings'].append("Aucune entité extraite")
                elif total_entities > 100:
                    validation_result['warnings'].append("Nombre d'entités très élevé - possible sur-extraction")
            
        except Exception as e:
            logger.error(f"Error validating function data for {operation_type}: {e}")
            validation_result['warnings'].append(f"Erreur de validation: {str(e)}")
        
        return validation_result
    
    def _enhance_content_analysis(self, content: str, operation_type: str) -> Dict[str, Any]:
        """
        Perform enhanced analysis on content responses.
        
        Args:
            content: Raw content from Albert API
            operation_type: Type of operation
            
        Returns:
            Dictionary with enhanced analysis results
        """
        analysis = {
            'content_length': len(content),
            'word_count': len(content.split()),
            'language_detected': 'french',  # Assume French for now
            'content_quality': 'good'
        }
        
        # Analyze content quality
        if len(content) < 20:
            analysis['content_quality'] = 'poor'
        elif len(content) < 50:
            analysis['content_quality'] = 'fair'
        elif len(content) > 2000:
            analysis['content_quality'] = 'verbose'
        
        # Detect specific patterns based on operation type
        if operation_type == 'summary':
            # Check for summary-like patterns
            summary_indicators = ['résumé', 'en résumé', 'points clés', 'important', 'urgent']
            found_indicators = [ind for ind in summary_indicators if ind.lower() in content.lower()]
            analysis['summary_indicators'] = found_indicators
            
        elif operation_type == 'answer':
            # Check for response patterns
            response_indicators = ['cordialement', 'salutations', 'merci', 'bonjour', 'bonsoir']
            found_indicators = [ind for ind in response_indicators if ind.lower() in content.lower()]
            analysis['response_indicators'] = found_indicators
            
        elif operation_type == 'classification':
            # Check for classification patterns
            classification_indicators = ['catégorie', 'classé', 'type', 'urgent', 'normal']
            found_indicators = [ind for ind in classification_indicators if ind.lower() in content.lower()]
            analysis['classification_indicators'] = found_indicators
            
        elif operation_type == 'sentiment':
            # Check for sentiment patterns
            positive_indicators = ['merci', 'excellent', 'parfait', 'bravo', 'félicitations']
            negative_indicators = ['problème', 'erreur', 'déçu', 'mécontent', 'urgent']
            neutral_indicators = ['information', 'demande', 'question', 'rappel']
            
            content_lower = content.lower()
            analysis['sentiment_indicators'] = {
                'positive': [ind for ind in positive_indicators if ind in content_lower],
                'negative': [ind for ind in negative_indicators if ind in content_lower],
                'neutral': [ind for ind in neutral_indicators if ind in content_lower]
            }
            
        elif operation_type == 'entities':
            # Check for entity patterns
            entity_patterns = {
                'date_patterns': ['aujourd\'hui', 'demain', 'lundi', 'mardi', 'janvier', 'février'],
                'person_patterns': ['monsieur', 'madame', 'docteur', 'professeur'],
                'org_patterns': ['société', 'entreprise', 'association', 'ministère'],
                'contact_patterns': ['@', 'tel:', 'tél:', 'phone:', 'email:']
            }
            
            content_lower = content.lower()
            found_patterns = {}
            for pattern_type, patterns in entity_patterns.items():
                found_patterns[pattern_type] = [p for p in patterns if p in content_lower]
            analysis['entity_patterns'] = found_patterns
        
        return analysis
