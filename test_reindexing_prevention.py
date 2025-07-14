#!/usr/bin/env python3
"""
Test script to demonstrate the improved RAG system without reindexing.

This script simulates multiple intelligent search requests to show that
the same emails are not reindexed multiple times.
"""

import json
import requests
import time
import logging

# Configure logging to see the detailed behavior
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8071"
API_ENDPOINT = f"{BASE_URL}/api/v1.0/chatbot/intelligent-search/"

# Sample test queries
TEST_QUERIES = [
    "aa",  # The same query from the logs
    "email",
    "test message",
    "aa"  # Repeat the first query to test reindexing prevention
]

def test_intelligent_search():
    """Test the intelligent search endpoint multiple times."""
    
    print("🚀 Testing Intelligent Search with Reindexing Prevention")
    print("=" * 60)
    
    # Note: In a real scenario, you would need proper authentication
    # For now, we'll just show the concept
    
    headers = {
        'Content-Type': 'application/json',
        # Add authentication headers here in real scenario
    }
    
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n📊 Test {i}: Searching for '{query}'")
        print("-" * 40)
        
        start_time = time.time()
        
        try:
            # Make the API request
            response = requests.post(
                API_ENDPOINT,
                headers=headers,
                json={"query": query},
                timeout=30
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"⏱️  Request completed in {duration:.2f} seconds")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    results_count = len(result.get('results', []))
                    total_emails = result.get('total_emails', 0)
                    print(f"✅ Success: Found {results_count} results from {total_emails} emails")
                    print(f"🔍 Summary: {result.get('search_summary', 'No summary')}")
                else:
                    print(f"❌ Search failed: {result.get('error', 'Unknown error')}")
            else:
                print(f"❌ HTTP Error {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        
        # Add a small delay between requests
        if i < len(TEST_QUERIES):
            print("⏳ Waiting 2 seconds before next request...")
            time.sleep(2)
    
    print("\n" + "=" * 60)
    print("📝 Expected Behavior:")
    print("- First request: Should index emails (longer duration)")
    print("- Subsequent requests: Should skip reindexing (faster)")
    print("- Last request: Should reuse indexed data (much faster)")
    print("\n✨ Check the backend logs to see detailed reindexing behavior!")

def show_expected_logs():
    """Show what to expect in the logs."""
    
    print("\n📋 Expected Log Messages:")
    print("=" * 50)
    
    expected_logs = [
        "🔍 First Request:",
        "  - 'No previous indexing hash found, indexing needed'",
        "  - 'Indexing 50 emails (reindexing needed)'",
        "  - 'Successfully indexed 50/50 emails'",
        "",
        "🔍 Subsequent Requests:",
        "  - 'Email set unchanged and recently indexed, skipping reindexing'",
        "  - 'Skipping indexing: emails already indexed and up to date'",
        "  - Much faster response times",
        "",
        "🔍 Collection Reuse:",
        "  - 'Using existing RAG collection: [collection_id]'",
        "  - 'Found [X] previously indexed emails'",
    ]
    
    for log in expected_logs:
        print(log)

if __name__ == "__main__":
    # Show expected behavior first
    show_expected_logs()
    
    print("\n" + "=" * 60)
    input("Press Enter to start the test (make sure the backend is running)...")
    
    # Run the test
    test_intelligent_search()
    
    print("\n🎯 To see the detailed logs, run:")
    print("   cd /Users/thomasgegout/Desktop/dinum/github3/s2025-p3-dty && make logs")
