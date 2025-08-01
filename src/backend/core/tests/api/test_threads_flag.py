"""Test threads delete."""

from django.urls import reverse
from django.utils import timezone

import pytest
from rest_framework import status

# Remove APIClient import if not used elsewhere after removing classes
# from rest_framework.test import APIClient
from core import (
    enums,
    factories,  # Renamed import
    models,  # Keep if models are used in remaining tests
)

pytestmark = pytest.mark.django_db

FLAG_API_URL = reverse("change-flag")

# Removed TestThreadsDelete class
# Removed TestThreadsBulkDelete class


def test_trash_single_thread_success(api_client):
    """Test marking a single thread as trashed successfully via flag endpoint."""
    user = factories.UserFactory()
    api_client.force_authenticate(user=user)
    mailbox = factories.MailboxFactory(users_read=[user])
    thread = factories.ThreadFactory()
    factories.ThreadAccessFactory(
        mailbox=mailbox,
        thread=thread,
        role=enums.ThreadAccessRoleChoices.EDITOR,
    )
    msg1 = factories.MessageFactory(thread=thread, is_trashed=False)
    msg2 = factories.MessageFactory(thread=thread, is_trashed=False)

    thread.refresh_from_db()
    thread.update_stats()
    assert thread.has_trashed is False
    assert msg1.is_trashed is False
    assert msg2.is_trashed is False

    data = {"flag": "trashed", "value": True, "thread_ids": [str(thread.id)]}
    response = api_client.post(FLAG_API_URL, data=data, format="json")

    assert response.status_code == status.HTTP_200_OK
    # Check that the response indicates update for messages within the thread
    assert response.data["updated_threads"] == 1

    # Verify thread trash flag is updated
    thread.refresh_from_db()
    assert thread.has_trashed is True

    # Verify all messages in the thread are marked as trashed
    msg1.refresh_from_db()
    msg2.refresh_from_db()
    assert msg1.is_trashed is True
    assert msg1.trashed_at is not None
    assert msg2.is_trashed is True
    assert msg2.trashed_at is not None


def test_untrash_single_thread_success(api_client):
    """Test marking a single thread as untrashed successfully via flag endpoint."""
    user = factories.UserFactory()
    api_client.force_authenticate(user=user)
    mailbox = factories.MailboxFactory(users_read=[user])
    thread = factories.ThreadFactory()
    factories.ThreadAccessFactory(
        mailbox=mailbox,
        thread=thread,
        role=enums.ThreadAccessRoleChoices.EDITOR,
    )
    trashed_time = timezone.now()
    msg1 = factories.MessageFactory(
        thread=thread, is_trashed=True, trashed_at=trashed_time
    )
    msg2 = factories.MessageFactory(
        thread=thread, is_trashed=True, trashed_at=trashed_time
    )

    thread.refresh_from_db()
    thread.update_stats()
    assert thread.has_trashed is True
    assert msg1.is_trashed is True
    assert msg2.is_trashed is True

    data = {"flag": "trashed", "value": False, "thread_ids": [str(thread.id)]}
    response = api_client.post(FLAG_API_URL, data=data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["updated_threads"] == 1

    # Verify thread trash flag is updated
    thread.refresh_from_db()
    assert thread.has_trashed is False

    # Verify all messages in the thread are marked as untrashed
    msg1.refresh_from_db()
    msg2.refresh_from_db()
    assert msg1.is_trashed is False
    assert msg1.trashed_at is None
    assert msg2.is_trashed is False
    assert msg2.trashed_at is None


def test_trash_multiple_threads_success(api_client):
    """Test marking multiple threads as trashed successfully."""
    user = factories.UserFactory()
    api_client.force_authenticate(user=user)
    mailbox = factories.MailboxFactory(users_read=[user])
    thread1 = factories.ThreadFactory()
    factories.ThreadAccessFactory(
        mailbox=mailbox,
        thread=thread1,
        role=enums.ThreadAccessRoleChoices.EDITOR,
    )
    factories.MessageFactory(thread=thread1, is_trashed=False)
    thread2 = factories.ThreadFactory()
    factories.ThreadAccessFactory(
        mailbox=mailbox,
        thread=thread2,
        role=enums.ThreadAccessRoleChoices.EDITOR,
    )
    factories.MessageFactory(thread=thread2, is_trashed=False)

    thread3 = (
        factories.ThreadFactory()
    )  # Already trashed (should be unaffected by value=true)
    factories.ThreadAccessFactory(
        mailbox=mailbox,
        thread=thread3,
        role=enums.ThreadAccessRoleChoices.EDITOR,
    )
    msg3 = factories.MessageFactory(
        thread=thread3, is_trashed=True, trashed_at=timezone.now()
    )

    thread1.refresh_from_db()
    thread1.update_stats()
    thread2.refresh_from_db()
    thread2.update_stats()
    thread3.refresh_from_db()
    thread3.update_stats()
    assert thread1.has_trashed is False
    assert thread2.has_trashed is False
    assert thread3.has_trashed is True

    thread_ids = [str(thread1.id), str(thread2.id), str(thread3.id)]
    data = {"flag": "trashed", "value": True, "thread_ids": thread_ids}
    response = api_client.post(FLAG_API_URL, data=data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["updated_threads"] == 3  # All 3 threads were targeted

    # Verify flags
    thread1.refresh_from_db()
    thread2.refresh_from_db()
    thread3.refresh_from_db()
    assert thread1.has_trashed is True
    assert thread2.has_trashed is True
    assert thread3.has_trashed is True  # Remains True

    # Verify messages
    assert thread1.messages.first().is_trashed is True
    assert thread2.messages.first().is_trashed is True
    msg3.refresh_from_db()
    assert msg3.is_trashed is True  # Remained trashed


def test_trash_thread_unauthorized(api_client):
    """Test trashing a thread without authentication."""
    thread = factories.ThreadFactory()
    data = {"flag": "trashed", "value": True, "thread_ids": [str(thread.id)]}
    response = api_client.post(FLAG_API_URL, data=data, format="json")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_trash_thread_no_permission(api_client):
    """Test trashing a thread the user doesn't have access to."""
    user = factories.UserFactory()
    api_client.force_authenticate(user=user)
    other_mailbox = factories.MailboxFactory()  # User does not have access
    thread = factories.ThreadFactory()
    factories.ThreadAccessFactory(
        mailbox=other_mailbox,
        thread=thread,
        role=enums.ThreadAccessRoleChoices.EDITOR,
    )
    factories.MessageFactory(thread=thread)

    initial_count = models.Thread.objects.count()

    data = {"flag": "trashed", "value": True, "thread_ids": [str(thread.id)]}
    response = api_client.post(FLAG_API_URL, data=data, format="json")

    # Should succeed but update nothing
    assert response.status_code == status.HTTP_200_OK
    assert response.data["updated_threads"] == 0

    # Verify thread and its messages are not marked as trashed
    thread.refresh_from_db()
    assert thread.has_trashed is False
    assert thread.messages.first().is_trashed is False
    assert (
        models.Thread.objects.count() == initial_count
    )  # Verify thread wasn't deleted


def test_trash_non_existent_thread(api_client):
    """Test trashing a thread that does not exist."""
    user = factories.UserFactory()
    api_client.force_authenticate(user=user)
    non_existent_uuid = "123e4567-e89b-12d3-a456-426614174000"

    data = {"flag": "trashed", "value": True, "thread_ids": [non_existent_uuid]}
    response = api_client.post(FLAG_API_URL, data=data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["updated_threads"] == 0
