"""
Tool definitions for Albert API function calling.

This module defines all available email processing tools that can be called
by the Albert API during conversations.
"""

from typing import List, Dict, Any


class EmailToolsDefinition:
    """Defines available email processing tools for function calling."""
    
    @staticmethod
    def get_email_tools() -> List[Dict[str, Any]]:
        """
        Define available email processing tools for function calling.
        
        Returns:
            List of tool definitions for Albert API function calling
        """
        return [
            {
                "name": "summarize_email",
                "description": "Résume le contenu d'un email en français avec les points clés et le niveau d'urgence. Récupère automatiquement l'email si une requête est fournie.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Requête pour rechercher et récupérer l'email à résumer (expéditeur, sujet, mots-clés)"
                        },
                        "email_content": {
                            "type": "string",
                            "description": "Le contenu de l'email à résumer (utilisé seulement si query n'est pas fourni)"
                        },
                        "sender": {
                            "type": "string", 
                            "description": "L'expéditeur de l'email (utilisé pour la recherche ou métadonnées)"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Le sujet de l'email (utilisé pour la recherche ou métadonnées)"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "generate_email_reply",
                "description": "Génère une réponse professionnelle à un email. Récupère automatiquement l'email si une requête est fournie. Peut créer un brouillon automatiquement.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Requête pour rechercher et récupérer l'email auquel répondre (expéditeur, sujet, mots-clés)"
                        },
                        "original_email": {
                            "type": "string",
                            "description": "Le contenu de l'email original auquel répondre (utilisé seulement si query n'est pas fourni)"
                        },
                        "context": {
                            "type": "string",
                            "description": "Contexte supplémentaire pour la réponse"
                        },
                        "tone": {
                            "type": "string",
                            "enum": ["professional", "friendly", "formal"],
                            "description": "Le ton souhaité pour la réponse",
                            "default": "professional"
                        },
                        "create_draft": {
                            "type": "boolean",
                            "description": "Si true, crée automatiquement un brouillon avec la réponse générée",
                            "default": False
                        },
                        "sender": {
                            "type": "string",
                            "description": "Expéditeur de l'email original (utilisé pour la recherche ou métadonnées)"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Sujet de l'email original (utilisé pour la recherche ou métadonnées)"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "classify_email",
                "description": "Classifie un email selon différentes catégories (urgent, normal, information, etc.). Récupère automatiquement l'email si une requête est fournie.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Requête pour rechercher et récupérer l'email à classifier (expéditeur, sujet, mots-clés)"
                        },
                        "email_content": {
                            "type": "string",
                            "description": "Le contenu de l'email à classifier (utilisé seulement si query n'est pas fourni)"
                        },
                        "sender": {
                            "type": "string",
                            "description": "L'expéditeur de l'email (utilisé pour la recherche ou métadonnées)"
                        },
                        "subject": {
                            "type": "string", 
                            "description": "Le sujet de l'email (utilisé pour la recherche ou métadonnées)"
                        }
                    },
                    "required": []
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
