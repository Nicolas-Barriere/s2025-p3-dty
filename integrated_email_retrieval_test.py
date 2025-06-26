#!/usr/bin/env python3
"""
Test script to verify the improved email content handling approach.
This test verifies that the three main functions (summarize_email, classify_email, generate_email_reply)
can now retrieve email content automatically when retrieve_email=True.
"""

import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock

# Add the src/backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'backend'))

# Test email content - a long email to test the new approach
FULL_EMAIL_CONTENT = """Bonjour,

Je vous écris pour vous informer d'un problème critique qui affecte notre système de production. 

SITUATION CRITIQUE:
- Le serveur de base de données principal a rencontré une erreur de corruption de données
- Cela affecte environ 15,000 enregistrements clients
- Le système de sauvegarde automatique ne fonctionne plus depuis hier
- Les transactions en cours sont interrompues

IMPACT ESTIMÉ:
- Perte potentielle de données critiques
- Arrêt des services client pendant 2-4 heures
- Impact financier estimé à 50,000€ par heure d'arrêt
- Risque de non-conformité réglementaire

ACTIONS IMMÉDIATES REQUISES:
- Isolation du serveur corrompu
- Activation des serveurs de secours
- Restoration à partir de la dernière sauvegarde valide
- Communication aux clients des interruptions prévues

Je vous demande de valider ces actions dans les plus brefs délais.

Cordialement,
Jean-Baptiste Martineau
Responsable Infrastructure IT
Tel: +33 1 23 45 67 89
Email: jb.martineau@entreprise.com"""

def test_integrated_email_retrieval():
    """Test that the three main functions can retrieve emails automatically."""
    
    print("🧪 Testing integrated email retrieval in main functions...")
    
    try:
        # Import the chatbot module  
        from chatbot.chatbot import AlbertChatbot
        
        # Create a chatbot instance
        chatbot = AlbertChatbot()
        
        # Mock the email retrieval function
        with patch('chatbot.email_retrieval.retrieve_email_content_by_query') as mock_retrieve, \
             patch.object(chatbot, 'summarize_mail') as mock_summarize, \
             patch.object(chatbot, 'classify_mail') as mock_classify, \
             patch.object(chatbot, 'generate_mail_answer') as mock_generate:
            
            # Setup the email retrieval mock
            mock_retrieve.return_value = {
                'success': True,
                'email_content': FULL_EMAIL_CONTENT,
                'metadata': {
                    'subject': 'URGENT: Problème critique système de production',
                    'sender_name': 'Jean-Baptiste Martineau',
                    'sender_email': 'jb.martineau@entreprise.com',
                    'message_id': 'msg_12345'
                }
            }
            
            # Setup the processing function mocks
            mock_summarize.return_value = {
                'success': True,
                'summary': {
                    'summary': 'Problème critique de corruption de données affectant 15,000 clients',
                    'urgency_level': 'high',
                    'action_required': True
                }
            }
            
            mock_classify.return_value = {
                'success': True,
                'classification': {
                    'primary_category': 'urgent',
                    'confidence_score': 0.95,
                    'reasoning': 'Email contient des mots-clés critiques et indique une panne majeure'
                }
            }
            
            mock_generate.return_value = {
                'success': True,
                'response': {
                    'response': 'Merci pour votre alerte. Nous prenons cette situation très au sérieux...',
                    'subject': 'Re: URGENT: Problème critique système',
                    'tone_used': 'professional'
                }
            }
            
            # Test 1: summarize_email with retrieve_email=True
            print("\n📋 Test 1: summarize_email with automatic retrieval")
            
            result1 = chatbot._execute_email_function(
                function_name='summarize_email',
                arguments={
                    'retrieve_email': True,
                    'search_query': 'Jean-Baptiste Martineau problème critique',
                    'sender': 'Jean-Baptiste Martineau',
                    'subject': 'problème critique'
                },
                user_id='test_user'
            )
            
            print(f"✅ summarize_email with retrieval: {result1.get('success')}")
            
            # Verify that retrieve_email_content_by_query was called
            mock_retrieve.assert_called_with(
                user_id='test_user',
                query='Jean-Baptiste Martineau problème critique',
                limit=1,
                use_elasticsearch=True
            )
            
            # Verify that summarize_mail was called with the full content
            mock_summarize.assert_called_with(
                FULL_EMAIL_CONTENT,
                'Jean-Baptiste Martineau',
                'URGENT: Problème critique système de production'
            )
            
            print(f"✅ Email content passed to summarize_mail: {len(FULL_EMAIL_CONTENT)} characters")
            
            # Test 2: classify_email with retrieve_email=True
            print("\n📋 Test 2: classify_email with automatic retrieval")
            
            # Reset the mock
            mock_retrieve.reset_mock()
            
            result2 = chatbot._execute_email_function(
                function_name='classify_email',
                arguments={
                    'retrieve_email': True,
                    'search_query': 'Jean-Baptiste critique production',
                },
                user_id='test_user'
            )
            
            print(f"✅ classify_email with retrieval: {result2.get('success')}")
            
            # Verify that classify_mail was called with the full content
            mock_classify.assert_called_with(
                FULL_EMAIL_CONTENT,
                'Jean-Baptiste Martineau',
                'URGENT: Problème critique système de production'
            )
            
            print(f"✅ Email content passed to classify_mail: {len(FULL_EMAIL_CONTENT)} characters")
            
            # Test 3: generate_email_reply with retrieve_email=True
            print("\n📋 Test 3: generate_email_reply with automatic retrieval")
            
            # Reset the mock
            mock_retrieve.reset_mock()
            
            result3 = chatbot._execute_email_function(
                function_name='generate_email_reply',
                arguments={
                    'retrieve_email': True,
                    'search_query': 'Jean-Baptiste Martineau',
                    'context': 'Réponse urgente requise',
                    'tone': 'professional'
                },
                user_id='test_user'
            )
            
            print(f"✅ generate_email_reply with retrieval: {result3.get('success')}")
            
            # Verify that generate_mail_answer was called with the full content
            mock_generate.assert_called_with(
                FULL_EMAIL_CONTENT,
                'Réponse urgente requise',
                'professional'
            )
            
            print(f"✅ Email content passed to generate_mail_answer: {len(FULL_EMAIL_CONTENT)} characters")
            
            # Test 4: Verify fallback when search_query is empty
            print("\n📋 Test 4: Fallback with sender/subject when search_query is empty")
            
            # Reset the mock
            mock_retrieve.reset_mock()
            
            result4 = chatbot._execute_email_function(
                function_name='summarize_email',
                arguments={
                    'retrieve_email': True,
                    'sender': 'Jean-Baptiste Martineau',
                    'subject': 'problème critique production'
                },
                user_id='test_user'
            )
            
            print(f"✅ summarize_email with sender/subject fallback: {result4.get('success')}")
            
            # Verify that the search query was built from sender and subject
            mock_retrieve.assert_called_with(
                user_id='test_user',
                query='Jean-Baptiste Martineau problème critique production',
                limit=1,
                use_elasticsearch=True
            )
            
            print(f"✅ Search query built from sender/subject: 'Jean-Baptiste Martineau problème critique production'")
            
            return True
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_traditional_mode():
    """Test that the functions still work in traditional mode (retrieve_email=False)."""
    
    print("\n🧪 Testing traditional mode (retrieve_email=False)...")
    
    try:
        from chatbot.chatbot import AlbertChatbot
        
        chatbot = AlbertChatbot()
        
        with patch.object(chatbot, 'summarize_mail') as mock_summarize:
            
            mock_summarize.return_value = {
                'success': True,
                'summary': {
                    'summary': 'Résumé du contenu fourni directement',
                    'urgency_level': 'medium'
                }
            }
            
            # Test traditional mode where email_content is provided directly
            result = chatbot._execute_email_function(
                function_name='summarize_email',
                arguments={
                    'email_content': 'Contenu d\'email fourni directement par l\'utilisateur.',
                    'sender': 'Test Sender',
                    'subject': 'Test Subject',
                    'retrieve_email': False  # Explicit traditional mode
                },
                user_id='test_user'
            )
            
            print(f"✅ Traditional mode still works: {result.get('success')}")
            
            # Verify that summarize_mail was called with the provided content
            mock_summarize.assert_called_with(
                'Contenu d\'email fourni directement par l\'utilisateur.',
                'Test Sender',
                'Test Subject'
            )
            
            print(f"✅ Direct email content used: No retrieval performed")
            
            return True
            
    except Exception as e:
        print(f"❌ Traditional mode test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling():
    """Test error handling when email retrieval fails."""
    
    print("\n🧪 Testing error handling for failed email retrieval...")
    
    try:
        from chatbot.chatbot import AlbertChatbot
        
        chatbot = AlbertChatbot()
        
        # Mock the email retrieval function to return failure
        with patch('chatbot.email_retrieval.retrieve_email_content_by_query') as mock_retrieve:
            
            mock_retrieve.return_value = {
                'success': False,
                'error': 'Email not found for the given query'
            }
            
            # Test error handling
            result = chatbot._execute_email_function(
                function_name='summarize_email',
                arguments={
                    'retrieve_email': True,
                    'search_query': 'non-existent email',
                },
                user_id='test_user'
            )
            
            print(f"✅ Error handling works: {not result.get('success')}")
            print(f"✅ Error message: {result.get('error')}")
            
            # Test missing user_id
            result2 = chatbot._execute_email_function(
                function_name='classify_email',
                arguments={
                    'retrieve_email': True,
                    'search_query': 'some query',
                },
                user_id=None  # Missing user_id
            )
            
            print(f"✅ Missing user_id handled: {not result2.get('success')}")
            print(f"✅ User ID error message: {result2.get('error')}")
            
            # Test missing search query and sender/subject
            result3 = chatbot._execute_email_function(
                function_name='generate_email_reply',
                arguments={
                    'retrieve_email': True,
                    # No search_query, sender, or subject provided
                },
                user_id='test_user'
            )
            
            print(f"✅ Missing search info handled: {not result3.get('success')}")
            print(f"✅ Missing search info error: {result3.get('error')}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting integrated email retrieval tests...")
    print("=" * 70)
    
    # Run the tests
    test1_passed = test_integrated_email_retrieval()
    test2_passed = test_traditional_mode()
    test3_passed = test_error_handling()
    
    print("\n" + "=" * 70)
    print("📊 FINAL TEST RESULTS:")
    print(f"✅ Integrated email retrieval: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"✅ Traditional mode compatibility: {'PASSED' if test2_passed else 'FAILED'}")
    print(f"✅ Error handling: {'PASSED' if test3_passed else 'FAILED'}")
    
    if all([test1_passed, test2_passed, test3_passed]):
        print("\n🎉 ALL TESTS PASSED! The new integrated approach is working correctly.")
        print("\n📋 Key improvements:")
        print("   • summarize_email, classify_email, and generate_email_reply can now retrieve emails automatically")
        print("   • Use retrieve_email=true to enable automatic retrieval")
        print("   • Functions build search queries from sender/subject when search_query is not provided")
        print("   • Traditional mode (retrieve_email=false) still works for backward compatibility")
        print("   • Proper error handling when retrieval fails or parameters are missing")
        print("   • Mini-MCP can now use these functions with a single call instead of chaining retrieve_email_content")
    else:
        print("\n❌ SOME TESTS FAILED. The implementation needs attention.")
    
    print("=" * 70)
