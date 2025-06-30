#!/usr/bin/env python3
"""
Test script to verify that draft creation works correctly with ThreadAccess.
"""

import sys
import os
import django
from django.conf import settings

# Add the backend src to Python PATH
sys.path.insert(0, '/Users/thomasgegout/Desktop/dinum/github/s2025-p3-dty/src/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'messages.settings')
django.setup()

from chatbot.email_writer import create_draft_email
from core.models import User, Mailbox, Thread

def test_draft_creation():
    """Test creating a draft and verify it's properly associated with mailbox."""
    
    # Get a user and mailbox
    user = User.objects.first()
    mailbox = Mailbox.objects.first()
    
    if not user or not mailbox:
        print("❌ No user or mailbox found in database")
        return False
    
    print(f"🧪 Testing draft creation with:")
    print(f"  User: {user.email}")
    print(f"  Mailbox: {mailbox.local_part}@{mailbox.domain.name}")
    
    # Count existing drafts
    initial_count = Thread.objects.filter(accesses__mailbox=mailbox, has_draft=True).count()
    print(f"  Initial draft count: {initial_count}")
    
    try:
        # Create a test draft
        result = create_draft_email(
            user_id=str(user.id),
            mailbox_id=str(mailbox.id),
            subject='🧪 TEST: ThreadAccess Draft Creation',
            body='This is a test draft to verify ThreadAccess is properly created.',
            recipients_to=[{'email': 'test-recipient@example.com', 'name': 'Test Recipient'}]
        )
        
        print(f"✅ Draft created successfully: {result}")
        
        # Verify the draft is associated with the mailbox
        final_count = Thread.objects.filter(accesses__mailbox=mailbox, has_draft=True).count()
        print(f"  Final draft count: {final_count}")
        
        if final_count == initial_count + 1:
            print("✅ Draft is properly associated with mailbox!")
            return True
        else:
            print("❌ Draft count didn't increase - ThreadAccess might not be working")
            return False
            
    except Exception as e:
        print(f"❌ Error creating draft: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🚀 Testing draft creation with ThreadAccess...")
    success = test_draft_creation()
    
    if success:
        print("\n🎉 All tests passed! Draft creation with ThreadAccess is working correctly.")
    else:
        print("\n💥 Tests failed! Check the logs above for details.")
        sys.exit(1)
