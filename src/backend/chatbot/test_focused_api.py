"""
Focused real API tests for individual chatbot functions.

This script allows testing individual functions with the real Albert API.
Useful for quick testing and debugging specific functionality.

Usage:
    python chatbot/test_focused_api.py --function summarize
    python chatbot/test_focused_api.py --function classify
    python chatbot/test_focused_api.py --function answer
"""

import os
import sys
import argparse
import json

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chatbot.chatbot import AlbertChatbot, AlbertConfig


def test_summarize_single():
    """Test summarization with a single email."""
    print("🔍 Testing Mail Summarization")
    print("-" * 40)
    
    # Create chatbot instance
    config = AlbertConfig()
    chatbot = AlbertChatbot(config)
    
    # Test email
    email_content = """
    Bonjour,
    
    Je vous écris pour signaler un problème urgent avec notre système de messagerie.
    Depuis ce matin, plusieurs utilisateurs ne peuvent plus envoyer d'emails.
    
    Le serveur SMTP semble être en panne et nous avons besoin d'une intervention
    technique immédiate pour résoudre ce problème.
    
    Pouvez-vous nous contacter rapidement ?
    
    Cordialement,
    Jean Dupont
    Responsable IT
    """
    
    sender = "jean.dupont@entreprise.fr"
    subject = "URGENT - Panne serveur SMTP"
    
    print(f"📧 Email à résumer:")
    print(f"De: {sender}")
    print(f"Sujet: {subject}")
    print(f"Contenu: {email_content.strip()}")
    
    try:
        print(f"\n🚀 Appel API Albert en cours...")
        result = chatbot.summarize_mail(email_content, sender, subject)
        
        print(f"\n📊 Résultat:")
        print(f"Success: {result['success']}")
        
        if result['success']:
            summary = result['summary']
            print(f"\n✅ RÉSUMÉ GÉNÉRÉ:")
            print(f"📝 Résumé: {summary['summary']}")
            print(f"🔑 Points clés:")
            for i, point in enumerate(summary['key_points'], 1):
                print(f"   {i}. {point}")
            print(f"⚡ Action requise: {'Oui' if summary['action_required'] else 'Non'}")
            print(f"🚨 Niveau d'urgence: {summary['urgency_level']}")
            
        else:
            print(f"❌ ERREUR: {result.get('error', 'Erreur inconnue')}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()


def test_classify_single():
    """Test classification with a single email."""
    print("📂 Testing Mail Classification")
    print("-" * 40)
    
    # Create chatbot instance
    config = AlbertConfig()
    chatbot = AlbertChatbot(config)
    
    # Test email
    email_content = """
    Félicitations pour votre excellent service !
    
    Je voulais simplement vous remercier pour la qualité de votre plateforme
    de messagerie. L'interface est intuitive et les fonctionnalités répondent
    parfaitement à nos besoins.
    
    Continuez ainsi !
    
    Bien cordialement,
    Marie Martin
    """
    
    sender = "marie.martin@client.com"
    subject = "Retour positif sur votre service"
    
    print(f"📧 Email à classifier:")
    print(f"De: {sender}")
    print(f"Sujet: {subject}")
    print(f"Contenu: {email_content.strip()}")
    
    try:
        print(f"\n🚀 Appel API Albert en cours...")
        result = chatbot.classify_mail(email_content, sender, subject)
        
        print(f"\n📊 Résultat:")
        print(f"Success: {result['success']}")
        
        if result['success']:
            classification = result['classification']
            print(f"\n✅ CLASSIFICATION GÉNÉRÉE:")
            print(f"📂 Catégorie principale: {classification['primary_category']}")
            
            if 'secondary_categories' in classification and classification['secondary_categories']:
                print(f"📂 Catégories secondaires: {', '.join(classification['secondary_categories'])}")
            
            print(f"🎯 Score de confiance: {classification['confidence_score']:.2f}")
            print(f"💭 Justification: {classification['reasoning']}")
            
            if classification.get('requires_human_review'):
                print(f"⚠️  Révision humaine recommandée")
            
            print(f"\n📋 Catégories disponibles: {', '.join(result['available_categories'])}")
            
        else:
            print(f"❌ ERREUR: {result.get('error', 'Erreur inconnue')}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()


def test_answer_single():
    """Test answer generation with a single email."""
    print("💬 Testing Mail Answer Generation")
    print("-" * 40)
    
    # Create chatbot instance
    config = AlbertConfig()
    chatbot = AlbertChatbot(config)
    
    # Original email to respond to
    original_email = """
    Bonjour,
    
    Pouvez-vous m'expliquer comment configurer les paramètres SMTP
    pour utiliser votre service avec Outlook ?
    
    J'ai essayé avec les paramètres standards mais je n'arrive pas
    à envoyer d'emails.
    
    Merci pour votre aide.
    
    Paul Durand
    """
    
    context = "Demande d'aide technique pour configuration Outlook"
    tone = "professional"
    
    print(f"📧 Email original:")
    print(f"{original_email.strip()}")
    print(f"\n🎯 Contexte: {context}")
    print(f"🎨 Ton demandé: {tone}")
    
    try:
        print(f"\n🚀 Appel API Albert en cours...")
        result = chatbot.generate_mail_answer(original_email, context, tone)
        
        print(f"\n📊 Résultat:")
        print(f"Success: {result['success']}")
        
        if result['success']:
            response = result['response']
            print(f"\n✅ RÉPONSE GÉNÉRÉE:")
            print(f"📧 Sujet: {response['subject']}")
            print(f"🎨 Ton utilisé: {response['tone_used']}")
            
            if 'estimated_reading_time' in response:
                print(f"⏱️  Temps de lecture estimé: {response['estimated_reading_time']}s")
            
            print(f"\n📝 Contenu de la réponse:")
            print("-" * 50)
            print(response['response'])
            print("-" * 50)
            
        else:
            print(f"❌ ERREUR: {result.get('error', 'Erreur inconnue')}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()


def test_api_connection():
    """Test basic API connection."""
    print("🔌 Testing API Connection")
    print("-" * 40)
    
    config = AlbertConfig()
    print(f"🌐 Base URL: {config.base_url}")
    print(f"🔑 API Key: {config.api_key[:20]}...")
    print(f"🤖 Model: {config.model}")
    
    chatbot = AlbertChatbot(config)
    
    # Simple test
    try:
        print(f"\n🚀 Test de connexion avec un email simple...")
        result = chatbot.summarize_mail(
            "Bonjour, ceci est un test de connexion à l'API Albert.",
            "test@example.com",
            "Test de connexion"
        )
        
        if result['success']:
            print(f"✅ Connexion réussie!")
            print(f"📝 Résumé de test: {result['summary']['summary']}")
        else:
            print(f"❌ Connexion échouée: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")


def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(description='Test individual Albert API functions')
    parser.add_argument(
        '--function', 
        choices=['summarize', 'classify', 'answer', 'connection'],
        default='connection',
        help='Function to test (default: connection)'
    )
    
    args = parser.parse_args()
    
    print("🧪 ALBERT API - TEST FOCALISÉ")
    print("=" * 50)
    
    if args.function == 'summarize':
        test_summarize_single()
    elif args.function == 'classify':
        test_classify_single()
    elif args.function == 'answer':
        test_answer_single()
    elif args.function == 'connection':
        test_api_connection()
    
    print("\n" + "=" * 50)
    print("✅ Test terminé!")


if __name__ == "__main__":
    main()
