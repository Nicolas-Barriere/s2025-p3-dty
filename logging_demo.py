#!/usr/bin/env python3
"""
Simple demonstration of the detailed logging functionality.

This script shows what the enhanced logging looks like when tools are called.
"""

import logging
import json
import time

# Configure logging to show detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("chatbot_logging_demo")

def demo_logging_output():
    """Demonstrate what the enhanced logging looks like."""
    
    print("="*80)
    print("🔧 CHATBOT DETAILED LOGGING DEMONSTRATION")
    print("="*80)
    print()
    
    print("This demonstrates the enhanced logging that has been added to the chatbot:")
    print()
    
    # Demo 1: Function execution start
    print("📋 1. FUNCTION EXECUTION START LOGGING:")
    print("-" * 50)
    function_name = "search_emails"
    arguments = {
        "query": "réunion importante projet Alpha",
        "limit": 10,
        "use_elasticsearch": True,
        "mailbox_id": "mailbox_123"
    }
    user_id = "user_456"
    
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
    
    print()
    
    # Demo 2: Mini-MCP iteration logging
    print("📋 2. MINI-MCP ITERATION LOGGING:")
    print("-" * 50)
    iteration = 1
    function_args = {
        "email_content": "Bonjour, je vous écris concernant la panne du serveur qui affecte notre production...",
        "categories": ["urgent", "support", "information"]
    }
    
    logger.info(f"Iteration {iteration}, Tool 1: Parsing tool call for classify_email")
    logger.info(f"Successfully parsed arguments for classify_email: {function_args}")
    logger.info(f"Iteration {iteration}, Tool 1: Executing classify_email with {len(function_args)} argument(s)")
    logger.info(f"🔧 Function: classify_email")
    logger.info(f"📋 Arguments Summary:")
    for key, value in function_args.items():
        if isinstance(value, str) and len(value) > 100:
            logger.info(f"  - {key}: '{value[:100]}...' ({len(value)} chars)")
        elif isinstance(value, (list, dict)):
            logger.info(f"  - {key}: {type(value).__name__} with {len(value)} items")
        else:
            logger.info(f"  - {key}: {value}")
    
    print()
    
    # Demo 3: Function completion logging
    print("📋 3. FUNCTION COMPLETION LOGGING:")
    print("-" * 50)
    execution_time = 1.25
    
    logger.info(f"✅ classify_email completed successfully (took {execution_time:.2f}s)")
    logger.info(f"📊 Result summary: Email classified as 'urgent' with 0.89 confidence")
    logger.info(f"✅ classify_email executed successfully")
    logger.info(f"⏱️ Execution time: {execution_time:.2f}s")
    
    print()
    
    # Demo 4: Error logging
    print("📋 4. ERROR LOGGING (when something goes wrong):")
    print("-" * 50)
    error_function = "retrieve_email_content"
    error_args = {"query": "email inexistant"}
    error_msg = "No email found matching the query"
    execution_time = 0.75
    
    logger.warning(f"⚠️ {error_function} failed (took {execution_time:.2f}s): {error_msg}")
    logger.error(f"❌ Function execution failed: {error_function} (took {execution_time:.2f}s)")
    logger.error(f"📝 Arguments: {json.dumps(error_args, indent=2, ensure_ascii=False)}")
    logger.error(f"💥 Error: {error_msg}")
    
    print()
    
    # Demo 5: Multi-step summary
    print("📋 5. MULTI-STEP SUMMARY LOGGING:")
    print("-" * 50)
    
    logger.info(f"📈 Iteration 1 summary: 2/2 successful tool calls")
    logger.info(f"🎯 Function execution completed - retrieve_email_content: success=True")
    logger.info(f"✅ Added success context: Email récupéré: 'Rapport mensuel' de Marie Dupont")
    logger.info(f"🎯 Function execution completed - summarize_email: success=True")
    logger.info(f"✅ Added success context: Email résumé avec succès")
    
    print()
    print("="*80)
    print("✅ LOGGING DEMONSTRATION COMPLETE")
    print("="*80)
    print()
    print("📝 KEY FEATURES OF THE ENHANCED LOGGING:")
    print("   🔧 Function name and execution start clearly logged")
    print("   📝 All arguments logged with types and preview for long strings")
    print("   ⏱️ Execution time tracking for performance monitoring")
    print("   ✅ Success/failure status for each function call")
    print("   📊 Result summaries with key metrics")
    print("   🎯 Step-by-step progress in multi-tool scenarios")
    print("   💥 Detailed error information with full context")
    print("   📈 Iteration summaries for complex workflows")
    print()
    print("This logging helps with:")
    print("   • Debugging function call issues")
    print("   • Understanding what arguments are passed")
    print("   • Performance monitoring")
    print("   • Tracking multi-step workflows")
    print("   • Identifying bottlenecks and failures")

if __name__ == "__main__":
    demo_logging_output()
