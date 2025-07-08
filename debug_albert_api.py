#!/usr/bin/env python3
"""
Debug script to test Albert API response directly
"""
import json
import re

# Test what the Albert API actually returns
def test_albert_api():
    """Test the Albert API directly with a simple request"""
    
    # This would need the actual Albert API URL and key
    # For now, let's create a mock response to test our parsing logic
    
    # Based on the logs, let's see what happens when we get different types of responses
    test_responses = [
        # Test 1: Normal response format
        '''Here are the relevant emails I found:

[{"id": "test-123", "relevance_score": 0.95, "reason": "Contains attachment"}]''',
        
        # Test 2: No JSON format
        '''I found some emails with attachments, but they are not in the correct format.''',
        
        # Test 3: Empty response
        '''I couldn't find any relevant emails.''',
        
        # Test 4: JSON with different format
        '''Found relevant emails:
[
  {
    "id": "email-1",
    "score": 0.9,
    "explanation": "Has attachments"
  }
]'''
    ]
    
    print("Testing different Albert API response formats:")
    print("=" * 60)
    
    for i, response in enumerate(test_responses, 1):
        print(f"\nTest {i}: Response length {len(response)} chars")
        print(f"Response: {response[:100]}...")
        
        # Test our parsing logic
        try:
            # Look for JSON array in the response
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                print(f"Found JSON: {json_str}")
                ai_results = json.loads(json_str)
                print(f"Parsed {len(ai_results)} results")
                for result in ai_results:
                    print(f"  - ID: {result.get('id', 'N/A')}, Score: {result.get('relevance_score', result.get('score', 'N/A'))}")
            else:
                print("No JSON array found in response")
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
        except Exception as e:
            print(f"Error: {e}")
        
        print("-" * 40)

if __name__ == "__main__":
    test_albert_api()
