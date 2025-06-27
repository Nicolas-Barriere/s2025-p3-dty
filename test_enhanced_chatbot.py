#!/usr/bin/env python3
"""
Enhanced Chatbot Integration Test
Tests the restored mini-MCP functionality and enhanced email processing features.
"""

import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock

# Add the backend source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'backend'))

def test_enhanced_email_processor():
    """Test the enhanced email processor with new features."""
    print("🔧 Testing Enhanced Email Processor...")
    
    # Import the enhanced email processor
    from chatbot.email_processor import EmailProcessor
    from chatbot.api_client import AlbertAPIClient
    from chatbot.email_parser import EmailParser
    
    # Mock the dependencies
    mock_api_client = Mock(spec=AlbertAPIClient)
    mock_parser = Mock(spec=EmailParser)
    
    # Create processor instance
    processor = EmailProcessor(mock_api_client, mock_parser)
    
    # Test email validation
    print("  📧 Testing email validation...")
    test_email = "Bonjour, ceci est un test d'email avec du contenu valide."
    validation_result = processor.validate_email_content(test_email, "test@example.com", "Test Subject")
    
    assert validation_result['is_valid'] == True
    assert 'warnings' in validation_result
    assert 'errors' in validation_result
    print("  ✅ Email validation works correctly")
    
    # Test metadata generation
    print("  📋 Testing metadata generation...")
    metadata_result = processor.generate_email_metadata(test_email, "test@example.com", "Test Subject")
    
    assert metadata_result['success'] == True
    assert 'metadata' in metadata_result
    assert metadata_result['metadata']['word_count'] > 0
    assert metadata_result['metadata']['detected_language'] == 'french'
    print("  ✅ Metadata generation works correctly")
    
    # Test batch processing structure
    print("  📦 Testing batch processing structure...")
    batch_emails = [
        ("Email 1 content", "sender1@example.com", "Subject 1"),
        ("Email 2 content", "sender2@example.com", "Subject 2")
    ]
    
    # Mock the API responses for batch processing
    mock_api_client.make_request.return_value = {
        'choices': [{
            'message': {
                'content': 'Test summary response'
            }
        }]
    }
    
    mock_parser.parse_summary_content.return_value = {
        'summary': 'Test summary',
        'key_points': ['Point 1', 'Point 2'],
        'urgency_level': 'medium'
    }
    
    batch_result = processor.process_mail_batch(batch_emails, 'summary')
    
    assert batch_result['success'] == True
    assert 'results' in batch_result
    assert len(batch_result['results']) == 2
    print("  ✅ Batch processing structure works correctly")
    
    print("✅ Enhanced Email Processor tests passed!")

def test_mini_mcp_conversation_handler():
    """Test the restored mini-MCP conversation handler."""
    print("🔧 Testing Mini-MCP Conversation Handler...")
    
    # Import the enhanced conversation handler
    from chatbot.conversation_handler import ConversationHandler
    from chatbot.api_client import AlbertAPIClient
    
    # Mock the API client
    mock_api_client = Mock(spec=AlbertAPIClient)
    
    # Create conversation handler instance
    handler = ConversationHandler(mock_api_client)
    
    # Test conversation memory
    print("  🧠 Testing conversation memory...")
    test_conversation_id = "test_conv_123"
    
    # Add some conversation history
    handler.add_conversation_turn(test_conversation_id, "user", "Hello, how are you?")
    handler.add_conversation_turn(test_conversation_id, "assistant", "I'm doing well, thank you!")
    
    # Retrieve conversation history
    history = handler.get_conversation_history(test_conversation_id)
    
    assert len(history) == 2
    assert history[0]['role'] == 'user'
    assert history[1]['role'] == 'assistant'
    print("  ✅ Conversation memory works correctly")
    
    # Test multi-step workflow detection
    print("  🔄 Testing multi-step workflow detection...")
    
    # Mock a multi-step query
    multi_step_query = "Can you analyze this email, classify it, and suggest a response?"
    
    # Mock API response with tool calls
    mock_api_client.make_request.return_value = {
        'choices': [{
            'message': {
                'tool_calls': [{
                    'type': 'function',
                    'function': {
                        'name': 'analyze_email_workflow',
                        'arguments': json.dumps({
                            'steps': ['analyze', 'classify', 'suggest_response'],
                            'email_content': 'Test email content'
                        })
                    }
                }]
            }
        }]
    }
    
    # Test workflow detection (would normally trigger multi-step processing)
    is_multi_step = handler._detect_multi_step_intent(multi_step_query)
    
    # This should detect multi-step intent based on keywords
    assert is_multi_step == True
    print("  ✅ Multi-step workflow detection works correctly")
    
    print("✅ Mini-MCP Conversation Handler tests passed!")

def test_content_analysis_enhancement():
    """Test the enhanced content analysis features."""
    print("🔧 Testing Enhanced Content Analysis...")
    
    from chatbot.email_processor import EmailProcessor
    from chatbot.api_client import AlbertAPIClient
    from chatbot.email_parser import EmailParser
    
    # Mock the dependencies
    mock_api_client = Mock(spec=AlbertAPIClient)
    mock_parser = Mock(spec=EmailParser)
    
    # Create processor instance
    processor = EmailProcessor(mock_api_client, mock_parser)
    
    # Test content analysis for different operation types
    test_content = "Bonjour, merci pour votre email. Cordialement, Jean."
    
    # Test summary analysis
    summary_analysis = processor._enhance_content_analysis(test_content, 'summary')
    assert 'content_length' in summary_analysis
    assert 'word_count' in summary_analysis
    assert summary_analysis['language_detected'] == 'french'
    print("  ✅ Summary content analysis works correctly")
    
    # Test sentiment analysis
    sentiment_analysis = processor._enhance_content_analysis(test_content, 'sentiment')
    assert 'sentiment_indicators' in sentiment_analysis
    assert 'positive' in sentiment_analysis['sentiment_indicators']
    print("  ✅ Sentiment content analysis works correctly")
    
    # Test entity analysis
    entity_analysis = processor._enhance_content_analysis(test_content, 'entities')
    assert 'entity_patterns' in entity_analysis
    assert 'person_patterns' in entity_analysis['entity_patterns']
    print("  ✅ Entity content analysis works correctly")
    
    print("✅ Enhanced Content Analysis tests passed!")

def test_function_data_validation():
    """Test the enhanced function data validation."""
    print("🔧 Testing Function Data Validation...")
    
    from chatbot.email_processor import EmailProcessor
    from chatbot.api_client import AlbertAPIClient
    from chatbot.email_parser import EmailParser
    
    # Mock the dependencies
    mock_api_client = Mock(spec=AlbertAPIClient)
    mock_parser = Mock(spec=EmailParser)
    
    # Create processor instance
    processor = EmailProcessor(mock_api_client, mock_parser)
    
    # Test summary validation
    good_summary = {
        'summary': 'This is a valid summary with sufficient length.',
        'key_points': ['Point 1', 'Point 2'],
        'urgency_level': 'medium'
    }
    
    validation_result = processor._validate_function_data('summary', good_summary)
    assert validation_result['is_valid'] == True
    assert len(validation_result['errors']) == 0
    print("  ✅ Summary validation works correctly")
    
    # Test sentiment validation
    good_sentiment = {
        'sentiment': 'positive',
        'emotional_tone': 'friendly',
        'confidence_score': 0.85,
        'key_emotions': ['grateful', 'pleased'],
        'response_suggestion': 'friendly'
    }
    
    validation_result = processor._validate_function_data('sentiment', good_sentiment)
    assert validation_result['is_valid'] == True
    print("  ✅ Sentiment validation works correctly")
    
    # Test entities validation
    good_entities = {
        'persons': ['Jean Dupont', 'Marie Martin'],
        'organizations': ['ACME Corp'],
        'dates': ['2024-01-15'],
        'locations': ['Paris']
    }
    
    validation_result = processor._validate_function_data('entities', good_entities)
    assert validation_result['is_valid'] == True
    print("  ✅ Entities validation works correctly")
    
    print("✅ Function Data Validation tests passed!")

def main():
    """Run all tests."""
    print("🚀 Starting Enhanced Chatbot Integration Tests...")
    print("=" * 60)
    
    try:
        test_enhanced_email_processor()
        print()
        test_mini_mcp_conversation_handler()
        print()
        test_content_analysis_enhancement()
        print()
        test_function_data_validation()
        print()
        
        print("=" * 60)
        print("🎉 All Enhanced Chatbot Integration Tests PASSED!")
        print("✅ Mini-MCP functionality has been successfully restored")
        print("✅ Email processor has been enhanced with advanced features")
        print("✅ Content analysis and validation are working correctly")
        print("✅ The chatbot is ready for enhanced conversational workflows")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
