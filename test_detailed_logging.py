#!/usr/bin/env python3
"""
Test script to demonstrate detailed logging of tool arguments in the chatbot system.

This script tests various email functions to show how arguments are logged.
"""

import os
import sys
import logging
import time

# Add the backend directory to Python path
backend_path = os.path.join(os.path.dirname(__file__), 'src', 'backend')
sys.path.insert(0, backend_path)

# Configure logging to see all the detailed logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('chatbot_logging_test.log')
    ]
)

logger = logging.getLogger(__name__)

def test_chatbot_with_detailed_logging():
    """Test the chatbot with various functions to see detailed argument logging."""
    
    try:
        # Import chatbot
        from chatbot.chatbot import get_chatbot
        
        logger.info("🚀 Starting detailed logging test for chatbot functions")
        
        # Create chatbot instance
        chatbot = get_chatbot()
        logger.info("✅ Chatbot instance created successfully")
        
        # Test cases with different types of arguments
        test_cases = [
            {
                "name": "Simple email search",
                "message": "Cherche des emails sur le sujet 'réunion'",
                "user_id": "test_user_123"
            },
            {
                "name": "Email summarization request",
                "message": "Résume l'email de Jean sur le projet Alpha",
                "user_id": "test_user_123"
            },
            {
                "name": "Email reply generation",
                "message": "Réponds à l'email de Marie concernant la formation",
                "user_id": "test_user_123"
            },
            {
                "name": "Get recent emails",
                "message": "Montre-moi mes emails récents",
                "user_id": "test_user_123"
            },
            {
                "name": "Complex multi-step request",
                "message": "Trouve l'email urgent de Pierre, résume-le et prépare une réponse",
                "user_id": "test_user_123"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"🧪 TEST CASE {i}: {test_case['name']}")
            logger.info(f"📝 Message: {test_case['message']}")
            logger.info(f"👤 User ID: {test_case['user_id']}")
            logger.info(f"{'='*60}")
            
            # Add a small delay between tests
            if i > 1:
                time.sleep(2)
            
            try:
                # Call the chatbot
                result = chatbot.process_user_message(
                    user_message=test_case['message'],
                    user_id=test_case['user_id'],
                    conversation_history=[]
                )
                
                logger.info(f"🎯 Test {i} result: success={result.get('success')}")
                logger.info(f"📊 Response type: {result.get('type', 'unknown')}")
                if result.get('success'):
                    response_preview = result.get('response', '')[:200]
                    logger.info(f"💬 Response preview: {response_preview}...")
                else:
                    logger.warning(f"❌ Test {i} failed: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                logger.error(f"❌ Test {i} crashed: {e}", exc_info=True)
            
            logger.info(f"✅ Test {i} completed")
        
        logger.info(f"\n{'='*60}")
        logger.info("🏁 All tests completed!")
        logger.info("📝 Check the logs above to see detailed argument logging")
        logger.info("📁 Full logs saved to: chatbot_logging_test.log")
        logger.info(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"💥 Test setup failed: {e}", exc_info=True)
        return False
    
    return True

if __name__ == "__main__":
    logger.info("🔧 Starting detailed logging test...")
    success = test_chatbot_with_detailed_logging()
    
    if success:
        logger.info("✅ Test completed successfully")
        print("\n" + "="*60)
        print("✅ DETAILED LOGGING TEST COMPLETED")
        print("📝 Check the console output above to see:")
        print("   • Function arguments logged with full details")
        print("   • Execution times for each function")
        print("   • Step-by-step mini-MCP progress")
        print("   • Success/failure status for each tool call")
        print("📁 Full logs also saved to: chatbot_logging_test.log")
        print("="*60)
        exit(0)
    else:
        logger.error("❌ Test failed")
        print("\n❌ TEST FAILED - Check the logs for details")
        exit(1)
