"""
Test functions for email retrieval functionality.

This module provides test functions to verify that the email retrieval
functions work correctly with the mailbox application database.
"""

import logging
import json
from typing import Dict, Any, List
from django.test import TestCase
from django.contrib.auth import get_user_model

from .email_retrieval import (
    get_user_accessible_mailboxes,
    get_mailbox_threads,
    get_thread_messages,
    get_message_by_id,
    get_parsed_message_content,
    search_messages,
    get_unread_messages,
    get_recent_messages,
    get_message_full_content
)

logger = logging.getLogger(__name__)
User = get_user_model()


def test_email_retrieval_basic():
    """
    Basic test function to check if email retrieval functions work.
    This can be called from Django shell or views for testing.
    """
    results = {
        'tests_run': 0,
        'tests_passed': 0,
        'tests_failed': 0,
        'errors': []
    }
    
    try:
        # Test 1: Get first user and their mailboxes
        results['tests_run'] += 1
        try:
            users = User.objects.all()[:1]
            if users:
                user = users[0]
                mailboxes = get_user_accessible_mailboxes(str(user.id))
                print(f"✓ Found {len(mailboxes)} mailboxes for user {user}")
                results['tests_passed'] += 1
            else:
                print("⚠ No users found in database")
                results['tests_passed'] += 1
        except Exception as e:
            error_msg = f"Error testing mailbox retrieval: {e}"
            print(f"✗ {error_msg}")
            results['errors'].append(error_msg)
            results['tests_failed'] += 1
        
        # Test 2: Get threads from first mailbox
        results['tests_run'] += 1
        try:
            from core.models import Mailbox
            mailboxes = Mailbox.objects.all()[:1]
            if mailboxes:
                mailbox = mailboxes[0]
                threads = get_mailbox_threads(str(mailbox.id), limit=5)
                print(f"✓ Found {len(threads)} threads for mailbox {mailbox}")
                results['tests_passed'] += 1
                
                # Test 3: Get messages from first thread
                results['tests_run'] += 1
                if threads:
                    thread = threads[0]
                    messages = get_thread_messages(str(thread.id))
                    print(f"✓ Found {len(messages)} messages in thread {thread}")
                    results['tests_passed'] += 1
                    
                    # Test 4: Get detailed content from first message
                    results['tests_run'] += 1
                    if messages:
                        message = messages[0]
                        content = get_parsed_message_content(message)
                        print(f"✓ Parsed content for message: {content.get('subject', 'No subject')}")
                        
                        # Test full content extraction
                        full_content = get_message_full_content(str(message.id))
                        print(f"✓ Full content length: {len(full_content)} characters")
                        results['tests_passed'] += 1
                    else:
                        print("⚠ No messages found in thread")
                        results['tests_passed'] += 1
                else:
                    print("⚠ No threads found in mailbox")
                    results['tests_passed'] += 1
                    results['tests_run'] += 1  # Skip message test
            else:
                print("⚠ No mailboxes found in database")
                results['tests_passed'] += 1
                results['tests_run'] += 2  # Skip thread and message tests
        except Exception as e:
            error_msg = f"Error testing thread/message retrieval: {e}"
            print(f"✗ {error_msg}")
            results['errors'].append(error_msg)
            results['tests_failed'] += 1
        
        # Test 5: Search functionality
        results['tests_run'] += 1
        try:
            if users:
                user = users[0]
                search_results = search_messages(str(user.id), query="", limit=5)
                print(f"✓ Search found {len(search_results)} messages")
                results['tests_passed'] += 1
            else:
                print("⚠ Skipping search test - no users")
                results['tests_passed'] += 1
        except Exception as e:
            error_msg = f"Error testing search functionality: {e}"
            print(f"✗ {error_msg}")
            results['errors'].append(error_msg)
            results['tests_failed'] += 1
        
        # Test 6: Unread messages
        results['tests_run'] += 1
        try:
            if users:
                user = users[0]
                unread_messages = get_unread_messages(str(user.id), limit=5)
                print(f"✓ Found {len(unread_messages)} unread messages")
                results['tests_passed'] += 1
            else:
                print("⚠ Skipping unread test - no users")
                results['tests_passed'] += 1
        except Exception as e:
            error_msg = f"Error testing unread messages: {e}"
            print(f"✗ {error_msg}")
            results['errors'].append(error_msg)
            results['tests_failed'] += 1
        
        # Test 7: Recent messages
        results['tests_run'] += 1
        try:
            if users:
                user = users[0]
                recent_messages = get_recent_messages(str(user.id), days=30, limit=5)
                print(f"✓ Found {len(recent_messages)} recent messages (last 30 days)")
                results['tests_passed'] += 1
            else:
                print("⚠ Skipping recent test - no users")
                results['tests_passed'] += 1
        except Exception as e:
            error_msg = f"Error testing recent messages: {e}"
            print(f"✗ {error_msg}")
            results['errors'].append(error_msg)
            results['tests_failed'] += 1
        
    except Exception as e:
        error_msg = f"Critical error in test setup: {e}"
        print(f"✗ {error_msg}")
        results['errors'].append(error_msg)
        results['tests_failed'] += 1
    
    # Print summary
    print(f"\n=== Test Summary ===")
    print(f"Tests run: {results['tests_run']}")
    print(f"Tests passed: {results['tests_passed']}")
    print(f"Tests failed: {results['tests_failed']}")
    
    if results['errors']:
        print(f"\nErrors:")
        for error in results['errors']:
            print(f"  - {error}")
    
    return results


def test_email_retrieval_with_chatbot_integration():
    """
    Test email retrieval functions with chatbot integration.
    This demonstrates how to use the retrieval functions with the chatbot.
    """
    try:
        from .chatbot import get_chatbot
        
        print("=== Testing Email Retrieval with Chatbot Integration ===")
        
        # Get chatbot instance
        chatbot = get_chatbot()
        
        # Get first user
        users = User.objects.all()[:1]
        if not users:
            print("⚠ No users found - cannot test")
            return {'error': 'No users found'}
        
        user = users[0]
        print(f"Testing with user: {user}")
        
        # Get recent messages for the user
        recent_messages = get_recent_messages(str(user.id), days=7, limit=3)
        
        if not recent_messages:
            print("⚠ No recent messages found - cannot test chatbot integration")
            return {'error': 'No recent messages found'}
        
        # Test chatbot integration with each message
        results = []
        for msg_info in recent_messages:
            print(f"\n--- Processing message: {msg_info['subject']} ---")
            
            # Get full message content
            full_content = get_message_full_content(msg_info['message_id'])
            
            if not full_content:
                print(f"⚠ Could not retrieve content for message {msg_info['message_id']}")
                continue
            
            print(f"Message content length: {len(full_content)} characters")
            
            # Test 1: Summarize the email
            try:
                summary_result = chatbot.summarize_mail(
                    mail_content=full_content,
                    sender=msg_info['sender_email'],
                    subject=msg_info['subject']
                )
                print(f"✓ Email summary generated: {summary_result.get('success', False)}")
                if summary_result.get('success'):
                    summary = summary_result.get('summary', {})
                    print(f"  Summary: {summary.get('summary', 'No summary')[:100]}...")
                
                results.append({
                    'message_id': msg_info['message_id'],
                    'subject': msg_info['subject'],
                    'summary_success': summary_result.get('success', False),
                    'summary': summary_result.get('summary', {})
                })
            except Exception as e:
                print(f"✗ Error summarizing email: {e}")
                results.append({
                    'message_id': msg_info['message_id'],
                    'subject': msg_info['subject'],
                    'summary_success': False,
                    'error': str(e)
                })
            
            # Test 2: Classify the email
            try:
                classification_result = chatbot.classify_mail(
                    mail_content=full_content,
                    sender=msg_info['sender_email'],
                    subject=msg_info['subject']
                )
                print(f"✓ Email classification generated: {classification_result.get('success', False)}")
                if classification_result.get('success'):
                    classification = classification_result.get('classification', {})
                    print(f"  Category: {classification.get('primary_category', 'Unknown')}")
                
                # Add classification to results
                for result in results:
                    if result['message_id'] == msg_info['message_id']:
                        result['classification_success'] = classification_result.get('success', False)
                        result['classification'] = classification_result.get('classification', {})
                        break
            except Exception as e:
                print(f"✗ Error classifying email: {e}")
                for result in results:
                    if result['message_id'] == msg_info['message_id']:
                        result['classification_success'] = False
                        result['classification_error'] = str(e)
                        break
        
        print(f"\n=== Integration Test Summary ===")
        print(f"Processed {len(results)} messages")
        successful_summaries = sum(1 for r in results if r.get('summary_success'))
        successful_classifications = sum(1 for r in results if r.get('classification_success'))
        print(f"Successful summaries: {successful_summaries}/{len(results)}")
        print(f"Successful classifications: {successful_classifications}/{len(results)}")
        
        return {
            'success': True,
            'messages_processed': len(results),
            'successful_summaries': successful_summaries,
            'successful_classifications': successful_classifications,
            'results': results
        }
        
    except Exception as e:
        error_msg = f"Critical error in chatbot integration test: {e}"
        print(f"✗ {error_msg}")
        return {'error': error_msg}


def test_function_calling_chatbot():
    """
    Test the new function calling approach with the chatbot.
    """
    try:
        from .chatbot import get_chatbot
        
        print("=== Testing Function Calling Chatbot ===")
        
        # Get chatbot instance
        chatbot = get_chatbot()
        
        # Get first user for testing
        users = User.objects.all()[:1]
        if not users:
            print("⚠ No users found - cannot test")
            return {'error': 'No users found'}
        
        user = users[0]
        user_id = str(user.id)
        print(f"Testing with user: {user}")
        
        # Test cases for function calling
        test_cases = [
            {
                'message': 'Peux-tu me montrer mes emails récents ?',
                'expected_function': 'get_recent_emails',
                'description': 'Test récupération emails récents'
            },
            {
                'message': 'Cherche des emails contenant "test"',
                'expected_function': 'search_emails', 
                'description': 'Test recherche d\'emails'
            },
            {
                'message': 'Résume cet email: "Bonjour, j\'ai un problème urgent avec mon ordinateur. Il ne démarre plus depuis ce matin. Pouvez-vous m\'aider rapidement ? Merci, Jean"',
                'expected_function': 'summarize_email',
                'description': 'Test résumé d\'email'
            },
            {
                'message': 'Génère une réponse à cet email: "Bonjour, j\'aimerais avoir plus d\'informations sur vos services. Cordialement, Marie"',
                'expected_function': 'generate_email_reply',
                'description': 'Test génération de réponse'
            },
            {
                'message': 'Classe cet email: "URGENT: Panne serveur - intervention immédiate requise"',
                'expected_function': 'classify_email',
                'description': 'Test classification d\'email'
            },
            {
                'message': 'Bonjour, comment ça va ?',
                'expected_function': None,
                'description': 'Test conversation normale (sans fonction)'
            }
        ]
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- Test {i}: {test_case['description']} ---")
            print(f"Message: {test_case['message']}")
            
            try:
                # Process the message with function calling
                response = chatbot.process_user_message(
                    user_message=test_case['message'],
                    user_id=user_id,
                    conversation_history=[]
                )
                
                print(f"✓ Response received: {response.get('success', False)}")
                print(f"Response type: {response.get('type', 'unknown')}")
                print(f"Function used: {response.get('function_used', 'None')}")
                print(f"Response preview: {response.get('response', '')[:100]}...")
                
                # Check if expected function was called
                function_used = response.get('function_used')
                expected_function = test_case['expected_function']
                
                test_result = {
                    'test_case': test_case['description'],
                    'message': test_case['message'],
                    'success': response.get('success', False),
                    'function_used': function_used,
                    'expected_function': expected_function,
                    'function_match': (function_used == expected_function) if expected_function else (function_used is None),
                    'response_type': response.get('type', 'unknown'),
                    'response_length': len(response.get('response', ''))
                }
                
                if test_result['function_match']:
                    print(f"✓ Function calling test passed")
                else:
                    print(f"⚠ Function calling mismatch: expected {expected_function}, got {function_used}")
                
                results.append(test_result)
                
            except Exception as e:
                print(f"✗ Error in test case: {e}")
                results.append({
                    'test_case': test_case['description'],
                    'message': test_case['message'],
                    'success': False,
                    'error': str(e)
                })
        
        # Summary
        print(f"\n=== Function Calling Test Summary ===")
        print(f"Total tests: {len(results)}")
        successful_tests = sum(1 for r in results if r.get('success'))
        function_matches = sum(1 for r in results if r.get('function_match'))
        print(f"Successful responses: {successful_tests}/{len(results)}")
        print(f"Correct function calls: {function_matches}/{len(results)}")
        
        # Detailed results
        for result in results:
            status = "✓" if result.get('success') else "✗"
            func_status = "✓" if result.get('function_match') else "⚠"
            print(f"{status}{func_status} {result['test_case']}: {result.get('function_used', 'None')}")
        
        return {
            'success': True,
            'total_tests': len(results),
            'successful_responses': successful_tests,
            'correct_function_calls': function_matches,
            'results': results
        }
        
    except Exception as e:
        error_msg = f"Critical error in function calling test: {e}"
        print(f"✗ {error_msg}")
        return {'error': error_msg}


# Update the run_all_tests function to include function calling test
def run_all_tests():
    """
    Run all email retrieval tests and return comprehensive results.
    """
    print("Starting comprehensive email retrieval tests...\n")
    
    # Run basic tests
    basic_results = test_email_retrieval_basic()
    
    print("\n" + "="*50)
    
    # Run chatbot integration tests
    integration_results = test_email_retrieval_with_chatbot_integration()
    
    print("\n" + "="*50)
    
    # Run function calling tests
    function_calling_results = test_function_calling_chatbot()
    
    return {
        'basic_tests': basic_results,
        'integration_tests': integration_results,
        'function_calling_tests': function_calling_results
    }


# Utility function for Django management command or shell
def quick_test():
    """
    Quick test function that can be called easily from Django shell.
    Usage: from chatbot.test_email_retrieval import quick_test; quick_test()
    """
    return test_email_retrieval_basic()


# Integration function for views
def test_specific_message(message_id: str) -> Dict[str, Any]:
    """
    Test chatbot functionality on a specific message.
    
    Args:
        message_id: UUID of the message to test
        
    Returns:
        Dictionary with test results
    """
    try:
        from .chatbot import get_chatbot
        
        # Get the message
        message = get_message_by_id(message_id)
        if not message:
            return {'error': f'Message {message_id} not found'}
        
        # Get full content
        full_content = get_message_full_content(message_id)
        if not full_content:
            return {'error': f'Could not retrieve content for message {message_id}'}
        
        # Get chatbot
        chatbot = get_chatbot()
        
        # Test summarization
        summary_result = chatbot.summarize_mail(
            mail_content=full_content,
            sender=message.sender.email,
            subject=message.subject
        )
        
        # Test classification
        classification_result = chatbot.classify_mail(
            mail_content=full_content,
            sender=message.sender.email,
            subject=message.subject
        )
        
        return {
            'success': True,
            'message_id': message_id,
            'subject': message.subject,
            'sender': message.sender.email,
            'content_length': len(full_content),
            'summary': summary_result,
            'classification': classification_result
        }
        
    except Exception as e:
        return {'error': str(e)}
