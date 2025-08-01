"""End-to-end tests for the OpenSearch search functionality."""

# pylint: disable=too-many-positional-arguments,unused-argument
import time

from django.conf import settings
from django.urls import reverse

import pytest
from rest_framework.test import APIClient

from core import enums
from core.factories import (
    ContactFactory,
    MailboxAccessFactory,
    MailboxFactory,
    MessageFactory,
    MessageRecipientFactory,
    ThreadAccessFactory,
    ThreadFactory,
    UserFactory,
)
from core.search import create_index_if_not_exists, delete_index, get_opensearch_client
from core.search.mapping import MESSAGE_INDEX


@pytest.fixture(name="setup_search")
def fixture_setup_search():
    """Setup OpenSearch index for testing."""

    delete_index()
    create_index_if_not_exists()

    # Check if OpenSearch is actually available
    es = get_opensearch_client()

    # pylint: disable=unexpected-keyword-arg
    es.cluster.health(wait_for_status="yellow", timeout=10)
    yield

    # Teardown
    try:
        delete_index()
    # pylint: disable=broad-exception-caught
    except Exception:
        pass


@pytest.fixture(name="test_user")
def fixture_test_user():
    """Create a test user."""
    return UserFactory()


@pytest.fixture(name="test_mailbox")
def fixture_test_mailbox(test_user):
    """Create a test mailbox with user access."""
    mailbox = MailboxFactory()
    MailboxAccessFactory(user=test_user, mailbox=mailbox)
    return mailbox


@pytest.fixture(name="api_client")
def fixture_api_client(test_user):
    """Create an authenticated API client."""
    client = APIClient()
    client.force_authenticate(user=test_user)
    return client


@pytest.fixture(name="test_url")
def fixture_test_url():
    """Get the thread list API URL."""
    return reverse("threads-list")


@pytest.fixture(name="wait_for_indexing")
def fixture_wait_for_indexing():
    """Fixture to create a function that waits for indexing to complete."""

    def _wait(max_retries=10, delay=0.5):
        """Wait for indexing to complete by refreshing the index."""
        es = get_opensearch_client()
        for _ in range(max_retries):
            try:
                es.indices.refresh(index=MESSAGE_INDEX)
                return True
            # pylint: disable=broad-exception-caught
            except Exception:
                time.sleep(delay)
        return False

    return _wait


@pytest.fixture(name="create_test_thread")
def fixture_create_test_thread(test_mailbox, wait_for_indexing):
    """Create a function to create test threads with messages."""

    def _create_thread_with_message(
        subject="Test Subject", content="Test content for search", mailbox=None
    ):
        """Create a thread with a message containing the given subject and content."""
        contact1 = ContactFactory(
            name="John Doe", email="john@example.com", mailbox=mailbox or test_mailbox
        )
        contact2 = ContactFactory(
            name="Jane Smith", email="jane@example.com", mailbox=mailbox or test_mailbox
        )

        thread = ThreadFactory(subject=subject)
        ThreadAccessFactory(thread=thread, mailbox=mailbox or test_mailbox)

        message = MessageFactory(
            thread=thread,
            subject=subject,
            sender=contact1,
            raw_mime=(
                f"From: {contact1.email}\r\n"
                f"To: {contact2.email}\r\n"
                f"Subject: {subject}\r\n"
                f"Content-Type: text/plain\r\n\r\n"
                f"{content}"
            ).encode("utf-8"),
        )

        MessageRecipientFactory(
            message=message, contact=contact2, type=enums.MessageRecipientTypeChoices.TO
        )

        # Wait for indexing to complete
        wait_for_indexing()

        return thread, message

    return _create_thread_with_message


@pytest.mark.skipif(
    len(settings.OPENSEARCH_HOSTS) == 0,
    reason="OpenSearch is not configured",
)
@pytest.mark.django_db
class TestSearchE2E:
    """End-to-end tests for OpenSearch search functionality."""

    def test_search_thread_by_subject(
        self, setup_search, api_client, test_url, create_test_thread
    ):
        """Test searching for a thread by its subject."""
        # Create a thread with a specific subject
        thread, _ = create_test_thread(
            subject="Meeting Agenda", content="Let's discuss the project status"
        )

        # Search for the thread
        response = api_client.get(f"{test_url}?search=Meeting")

        # Verify response
        assert response.status_code == 200

        # Check if the thread is found
        thread_ids = [t["id"] for t in response.data["results"]]
        assert str(thread.id) in thread_ids

    def test_search_thread_by_message_content(
        self, setup_search, api_client, test_url, create_test_thread
    ):
        """Test searching for a thread by message content."""
        # Create a thread with specific content
        thread, _ = create_test_thread(
            subject="Status Update", content="The project is making good progress"
        )

        # Search for the thread
        response = api_client.get(f"{test_url}?search=progress")

        # Verify response
        assert response.status_code == 200

        # Check if the thread is found
        thread_ids = [t["id"] for t in response.data["results"]]
        assert str(thread.id) in thread_ids

    def test_search_with_filters(
        self,
        setup_search,
        api_client,
        test_url,
        create_test_thread,
        wait_for_indexing,
    ):
        """Test searching with additional filters."""
        # Create a thread with unread status
        thread, message = create_test_thread(
            subject="Important Notification", content="Please review the document"
        )
        # Search for the thread with unread filter
        response = api_client.get(f"{test_url}?search=Notification is:unread")

        # Verify response
        assert response.status_code == 200

        # Check if the thread is found
        assert len(response.data["results"]) == 0

        # Update the message to be unread
        message.is_unread = True
        message.save()

        # Wait for indexing to complete
        wait_for_indexing()

        # Search for the thread with unread filter
        response = api_client.get(f"{test_url}?search=Notification is:unread")

        # Verify response
        assert response.status_code == 200

        # Check if the thread is found
        thread_ids = [t["id"] for t in response.data["results"]]
        assert str(thread.id) in thread_ids

    def test_multiple_threads_in_search_results(
        self,
        setup_search,
        api_client,
        test_url,
        create_test_thread,
        test_mailbox,
    ):
        """Test that multiple relevant threads are returned in search results."""
        # Create two threads with the same keyword
        thread1, _ = create_test_thread(
            subject="Project Alpha",
            content="This is about project",
            mailbox=test_mailbox,
        )
        thread2, _ = create_test_thread(
            subject="Project Beta",
            content="Another project update",
            mailbox=test_mailbox,
        )

        # Search for the threads
        response = api_client.get(f"{test_url}?search=project")

        # Verify response
        assert response.status_code == 200

        # Check if both threads are found
        thread_ids = [t["id"] for t in response.data["results"]]
        assert str(thread1.id) in thread_ids
        assert str(thread2.id) in thread_ids
        assert len(thread_ids) >= 2
