"""
Real API tests for the Albert chatbot functionality.

These tests make actual calls to the Albert API and should be run carefully
to avoid excessive API usage. Set ALBERT_API_KEY environment variable
or use the default key for testing.

Usage:
    export ALBERT_API_KEY="your-api-key"
    python chatbot/test_real_api.py
"""

import os
import sys
import time
import json
from typing import Dict, Any

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chatbot.chatbot import AlbertChatbot, AlbertConfig, MailClassification


class RealAPITester:
    """Test runner for real Albert API calls."""

    def __init__(self, api_key: str = None):
        """Initialize with API key."""
        # Use provided key or environment variable or default
        self.api_key = (
            api_key or 
            os.getenv('ALBERT_API_KEY') or 
            "sk-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo0NTQsInRva2VuX2lkIjoxNjM5LCJleHBpcmVzX2F0IjoxNzgxNzMzNjAwfQ.CwVlU_n4uj6zsfxZV1AFLxfwqzd7puYzs4Agp8HhYxs"
        )
        
        self.config = AlbertConfig(api_key=self.api_key)
        self.chatbot = AlbertChatbot(self.config)
        
        # Test data
        self.test_emails = [
            {
                'content': 'Bonjour, je souhaiterais avoir des informations sur votre service de messagerie. '
                          'Pouvez-vous me dire quels sont les tarifs et les fonctionnalités disponibles ? '
                          'J\'ai besoin de cette information rapidement pour mon projet. Merci de votre retour.',
                'sender': 'client.test@example.com',
                'subject': 'Demande d\'informations sur le service'
            },
            {
                'content': 'URGENT: Le service de messagerie ne fonctionne plus depuis ce matin. '
                          'Plusieurs utilisateurs sont affectés et ne peuvent plus envoyer d\'emails. '
                          'Merci de traiter ce problème en priorité absolue.',
                'sender': 'support@entreprise.fr',
                'subject': 'URGENT - Panne du service messagerie'
            },
            {
                'content': 'Félicitations pour votre nouveau service ! '
                          'Je voulais juste vous faire savoir que l\'interface est très bien conçue '
                          'et que l\'expérience utilisateur est excellente. Continuez comme ça !',
                'sender': 'feedback@utilisateur.com',
                'subject': 'Félicitations pour le nouveau service'
            },
            {
                'content': 'Pouvez-vous m\'expliquer comment configurer les paramètres SMTP pour '
                          'mon client de messagerie ? J\'ai essayé avec les paramètres standard '
                          'mais cela ne fonctionne pas. Avez-vous une documentation technique ?',
                'sender': 'technicien@societe.org',
                'subject': 'Configuration SMTP - Aide technique'
            }
        ]

    def print_separator(self, title: str):
        """Print a formatted separator."""
        print("\n" + "="*60)
        print(f"📧 {title}")
        print("="*60)

    def print_result(self, result: Dict[str, Any], operation: str):
        """Print formatted result."""
        if result['success']:
            print(f"✅ {operation} - SUCCESS")
            
            if operation == "SUMMARIZATION":
                summary = result['summary']
                print(f"📝 Résumé: {summary['summary']}")
                print(f"🔑 Points clés: {', '.join(summary['key_points'])}")
                print(f"⚡ Action requise: {'Oui' if summary['action_required'] else 'Non'}")
                print(f"🚨 Urgence: {summary['urgency_level']}")
                
            elif operation == "CLASSIFICATION":
                classification = result['classification']
                print(f"📂 Catégorie: {classification['primary_category']}")
                if 'secondary_categories' in classification:
                    print(f"📂 Catégories secondaires: {', '.join(classification['secondary_categories'])}")
                print(f"🎯 Confiance: {classification['confidence_score']:.2f}")
                print(f"💭 Justification: {classification['reasoning']}")
                if classification.get('requires_human_review'):
                    print("⚠️  Révision humaine recommandée")
                    
            elif operation == "ANSWER GENERATION":
                response = result['response']
                print(f"📧 Sujet: {response['subject']}")
                print(f"🎨 Ton: {response['tone_used']}")
                print(f"📝 Réponse: {response['response'][:200]}...")
                if 'estimated_reading_time' in response:
                    print(f"⏱️  Temps de lecture: {response['estimated_reading_time']}s")
        else:
            print(f"❌ {operation} - FAILED")
            print(f"Error: {result.get('error', 'Unknown error')}")

    def test_summarize_mail(self):
        """Test real API mail summarization."""
        self.print_separator("TEST SUMMARIZATION")
        
        for i, email in enumerate(self.test_emails, 1):
            print(f"\n📧 Email {i}:")
            print(f"De: {email['sender']}")
            print(f"Sujet: {email['subject']}")
            print(f"Contenu: {email['content'][:100]}...")
            
            try:
                result = self.chatbot.summarize_mail(
                    email['content'],
                    email['sender'],
                    email['subject']
                )
                self.print_result(result, "SUMMARIZATION")
                
            except Exception as e:
                print(f"❌ Exception: {e}")
            
            # Rate limiting - wait between requests
            time.sleep(1)

    def test_classify_mail(self):
        """Test real API mail classification."""
        self.print_separator("TEST CLASSIFICATION")
        
        for i, email in enumerate(self.test_emails, 1):
            print(f"\n📧 Email {i}:")
            print(f"De: {email['sender']}")
            print(f"Sujet: {email['subject']}")
            
            try:
                result = self.chatbot.classify_mail(
                    email['content'],
                    email['sender'],
                    email['subject']
                )
                self.print_result(result, "CLASSIFICATION")
                
            except Exception as e:
                print(f"❌ Exception: {e}")
            
            # Rate limiting - wait between requests
            time.sleep(1)

    def test_generate_mail_answer(self):
        """Test real API mail answer generation."""
        self.print_separator("TEST ANSWER GENERATION")
        
        # Test with different tones
        tones = ['professional', 'friendly', 'formal']
        
        for i, (email, tone) in enumerate(zip(self.test_emails[:3], tones), 1):
            print(f"\n📧 Réponse à l'email {i} (ton: {tone}):")
            print(f"Email original: {email['content'][:100]}...")
            
            try:
                result = self.chatbot.generate_mail_answer(
                    email['content'],
                    context=f"Email reçu de {email['sender']}",
                    tone=tone
                )
                self.print_result(result, "ANSWER GENERATION")
                
            except Exception as e:
                print(f"❌ Exception: {e}")
            
            # Rate limiting - wait between requests
            time.sleep(2)

    def test_custom_categories(self):
        """Test classification with custom categories."""
        self.print_separator("TEST CUSTOM CATEGORIES")
        
        custom_categories = ['facturation', 'technique', 'commercial', 'general']
        
        email = self.test_emails[0]  # Use first email
        print(f"📧 Email à classifier:")
        print(f"Contenu: {email['content'][:100]}...")
        print(f"Catégories personnalisées: {', '.join(custom_categories)}")
        
        try:
            result = self.chatbot.classify_mail(
                email['content'],
                email['sender'],
                email['subject'],
                custom_categories=custom_categories
            )
            self.print_result(result, "CLASSIFICATION (CUSTOM)")
            
        except Exception as e:
            print(f"❌ Exception: {e}")

    def test_batch_processing(self):
        """Test real API batch processing."""
        self.print_separator("TEST BATCH PROCESSING")
        
        # Prepare batch data
        batch_mails = [
            {
                'content': email['content'],
                'sender': email['sender'],
                'subject': email['subject']
            }
            for email in self.test_emails[:2]  # Use first 2 emails to avoid too many API calls
        ]
        
        operations = ['summarize', 'classify']
        
        for operation in operations:
            print(f"\n🔄 Traitement en lot - Opération: {operation}")
            print(f"Nombre d'emails: {len(batch_mails)}")
            
            try:
                results = self.chatbot.process_mail_batch(batch_mails, operation)
                
                print(f"✅ Traitement terminé - {len(results)} résultats")
                
                for result in results:
                    batch_index = result.get('batch_index', 'N/A')
                    success = result.get('success', False)
                    print(f"  📧 Email {batch_index}: {'✅' if success else '❌'}")
                    
                    if not success:
                        print(f"    Error: {result.get('error', 'Unknown')}")
                
            except Exception as e:
                print(f"❌ Exception: {e}")
            
            # Wait between operations
            time.sleep(2)

    def test_complete_workflow(self):
        """Test a complete workflow: classify → summarize → generate answer."""
        self.print_separator("TEST COMPLETE WORKFLOW")
        
        email = self.test_emails[1]  # Use urgent email
        print(f"📧 Email pour workflow complet:")
        print(f"De: {email['sender']}")
        print(f"Sujet: {email['subject']}")
        print(f"Contenu: {email['content'][:150]}...")
        
        try:
            # Step 1: Classify
            print(f"\n🔍 Étape 1: Classification")
            classify_result = self.chatbot.classify_mail(
                email['content'],
                email['sender'],
                email['subject']
            )
            
            if classify_result['success']:
                category = classify_result['classification']['primary_category']
                confidence = classify_result['classification']['confidence_score']
                print(f"✅ Classifié comme: {category} (confiance: {confidence:.2f})")
            else:
                print(f"❌ Classification échouée: {classify_result.get('error')}")
                return
            
            time.sleep(1)
            
            # Step 2: Summarize
            print(f"\n📝 Étape 2: Résumé")
            summarize_result = self.chatbot.summarize_mail(
                email['content'],
                email['sender'],
                email['subject']
            )
            
            if summarize_result['success']:
                urgency = summarize_result['summary']['urgency_level']
                action_required = summarize_result['summary']['action_required']
                print(f"✅ Résumé généré - Urgence: {urgency}, Action requise: {action_required}")
            else:
                print(f"❌ Résumé échoué: {summarize_result.get('error')}")
                return
            
            time.sleep(1)
            
            # Step 3: Generate response
            print(f"\n💬 Étape 3: Génération de réponse")
            context = f"Email classifié comme {category} avec urgence {urgency}"
            
            answer_result = self.chatbot.generate_mail_answer(
                email['content'],
                context=context,
                tone='professional'
            )
            
            if answer_result['success']:
                subject = answer_result['response']['subject']
                print(f"✅ Réponse générée - Sujet: {subject}")
                print(f"📝 Aperçu: {answer_result['response']['response'][:200]}...")
            else:
                print(f"❌ Génération de réponse échouée: {answer_result.get('error')}")
            
            print(f"\n🎉 Workflow complet terminé avec succès!")
            
        except Exception as e:
            print(f"❌ Exception dans le workflow: {e}")

    def test_error_scenarios(self):
        """Test error handling scenarios."""
        self.print_separator("TEST ERROR SCENARIOS")
        
        # Test with empty content
        print("\n📝 Test avec contenu vide:")
        try:
            result = self.chatbot.summarize_mail("", "test@example.com", "Empty")
            print(f"Résultat: {'✅' if result['success'] else '❌'}")
            if not result['success']:
                print(f"Error: {result.get('error')}")
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        time.sleep(1)
        
        # Test with very long content
        print("\n📝 Test avec contenu très long:")
        long_content = "Test content. " * 500  # Very long content
        try:
            result = self.chatbot.summarize_mail(
                long_content,
                "test@example.com", 
                "Long Content Test"
            )
            print(f"Résultat: {'✅' if result['success'] else '❌'}")
            if result['success']:
                print(f"Résumé: {result['summary']['summary'][:100]}...")
        except Exception as e:
            print(f"❌ Exception: {e}")

    def run_all_tests(self):
        """Run all real API tests."""
        print("🚀 ALBERT API - TESTS RÉELS")
        print(f"🔑 API Key: {self.api_key[:20]}...")
        print(f"🌐 Base URL: {self.config.base_url}")
        print(f"🤖 Model: {self.config.model}")
        
        try:
            # Run all tests
            self.test_summarize_mail()
            self.test_classify_mail()
            self.test_generate_mail_answer()
            self.test_custom_categories()
            self.test_batch_processing()
            self.test_complete_workflow()
            self.test_error_scenarios()
            
            print("\n" + "="*60)
            print("🎉 TOUS LES TESTS RÉELS TERMINÉS!")
            print("="*60)
            
        except KeyboardInterrupt:
            print("\n⚠️  Tests interrompus par l'utilisateur")
        except Exception as e:
            print(f"\n❌ Erreur générale: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("⚠️  ATTENTION: Ces tests utilisent l'API Albert réelle!")
    print("Assurez-vous d'avoir une clé API valide et de respecter les limites d'usage.")
    
    # Ask for confirmation
    confirm = input("\nVoulez-vous continuer? (oui/non): ").lower().strip()
    if confirm not in ['oui', 'o', 'yes', 'y']:
        print("Tests annulés.")
        sys.exit(0)
    
    # Optional: custom API key
    custom_key = input("\nClé API personnalisée (Entrée pour utiliser la clé par défaut): ").strip()
    
    # Run tests
    tester = RealAPITester(api_key=custom_key if custom_key else None)
    tester.run_all_tests()
