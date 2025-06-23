"""
Django management command to test email retrieval functions.

Usage:
    python manage.py test_email_retrieval
    python manage.py test_email_retrieval --with-chatbot
    python manage.py test_email_retrieval --message-id <message_id>
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from chatbot.test_email_retrieval import (
    run_all_tests,
    test_specific_message,
    quick_test,
    test_function_calling_chatbot
)


class Command(BaseCommand):
    help = 'Test email retrieval functions for chatbot integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--with-chatbot',
            action='store_true',
            help='Include chatbot integration tests',
        )
        parser.add_argument(
            '--message-id',
            type=str,
            help='Test with a specific message ID',
        )
        parser.add_argument(
            '--function-calling',
            action='store_true',
            help='Test function calling approach',
        )
        parser.add_argument(
            '--quick',
            action='store_true',
            help='Run quick basic tests only',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting email retrieval tests...')
        )

        try:
            if options['message_id']:
                # Test specific message
                self.stdout.write(f"Testing specific message: {options['message_id']}")
                result = test_specific_message(options['message_id'])
                self.stdout.write(str(result))
                
            elif options['function_calling']:
                # Function calling test
                self.stdout.write("Testing function calling approach...")
                result = test_function_calling_chatbot()
                
            elif options['quick']:
                # Quick test
                self.stdout.write("Running quick basic tests...")
                result = quick_test()
                
            elif options['with_chatbot']:
                # Full test suite with chatbot
                self.stdout.write("Running full test suite with chatbot integration...")
                result = run_all_tests()
                
            else:
                # Basic tests only
                self.stdout.write("Running basic email retrieval tests...")
                from chatbot.test_email_retrieval import test_email_retrieval_basic
                result = test_email_retrieval_basic()

            self.stdout.write(
                self.style.SUCCESS('Tests completed successfully!')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error running tests: {e}')
            )
