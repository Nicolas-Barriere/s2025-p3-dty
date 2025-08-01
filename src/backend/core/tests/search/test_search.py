"""Tests for the core.search module."""

from unittest import mock

from django.test import override_settings

import pytest

from core.factories import (
    MailboxFactory,
    MessageFactory,
    ThreadAccessFactory,
    ThreadFactory,
)
from core.search import (
    create_index_if_not_exists,
    delete_index,
    index_message,
    index_thread,
    reindex_all,
    reindex_mailbox,
    search_threads,
)


@pytest.fixture(name="mock_es_client_search")
def fixture_mock_es_client_search():
    """Mock the OpenSearch client."""
    with mock.patch(
        "core.search.search.get_opensearch_client"
    ) as mock_get_opensearch_client:
        mock_es = mock.MagicMock()
        # Setup standard mock returns
        mock_es.indices.exists.return_value = False
        mock_es.indices.create.return_value = {"acknowledged": True}
        mock_es.indices.delete.return_value = {"acknowledged": True}

        # Setup search mock
        mock_es.search.return_value = {"hits": {"total": {"value": 0}, "hits": []}}

        mock_get_opensearch_client.return_value = mock_es
        mock_es.reset_mock()
        yield mock_es


@pytest.fixture(name="mock_es_client_index")
def fixture_mock_es_client_index():
    """Mock the OpenSearch client."""
    with mock.patch(
        "core.search.index.get_opensearch_client"
    ) as mock_get_opensearch_client:
        mock_es = mock.MagicMock()
        # Setup standard mock returns
        mock_es.indices.exists.return_value = False
        mock_es.indices.create.return_value = {"acknowledged": True}
        mock_es.indices.delete.return_value = {"acknowledged": True}

        # Setup search mock
        mock_es.search.return_value = {"hits": {"total": {"value": 0}, "hits": []}}

        mock_get_opensearch_client.return_value = mock_es
        mock_es.reset_mock()
        yield mock_es


@pytest.fixture(name="test_thread")
def fixture_test_thread(test_mailbox):
    """Create a test thread with a message."""
    thread = ThreadFactory()
    ThreadAccessFactory(mailbox=test_mailbox, thread=thread)
    MessageFactory(thread=thread)
    return thread


@pytest.fixture(name="test_mailbox")
def fixture_test_mailbox():
    """Create a test mailbox."""
    return MailboxFactory()


def test_create_index_if_not_exists(mock_es_client_index):
    """Test creating the OpenSearch index."""
    # Reset mock and configure
    mock_es_client_index.indices.exists.return_value = False

    # Call the function
    create_index_if_not_exists()

    # Verify the appropriate ES client calls were made
    mock_es_client_index.indices.exists.assert_called_once()
    mock_es_client_index.indices.create.assert_called_once()


def test_delete_index(mock_es_client_index):
    """Test deleting the OpenSearch index."""

    # Call the function
    delete_index()

    # Verify the ES client call
    mock_es_client_index.indices.delete.assert_called_once()


@pytest.mark.django_db
def test_index_thread(mock_es_client_index, test_thread):
    """Test indexing a thread."""

    # Call the function
    success = index_thread(test_thread)

    # Verify result
    assert success

    # Verify ES client was called
    assert mock_es_client_index.index.call_count > 0


@pytest.mark.django_db
def test_index_message(mock_es_client_index, test_thread):
    """Test indexing a message."""
    message = test_thread.messages.first()

    # Call the function
    success = index_message(message)

    # Verify result
    assert success

    # Verify ES client call
    mock_es_client_index.index.assert_called()


@pytest.mark.django_db
def test_reindex_all(mock_es_client_index):
    """Test reindexing all threads and messages."""
    # Reset mock
    mock_es_client_index.indices.exists.return_value = False

    # Call the function
    result = reindex_all()

    # Verify result
    assert result["status"] == "success"

    # Verify ES client calls
    mock_es_client_index.indices.delete.assert_called_once()
    mock_es_client_index.indices.create.assert_called_once()


@pytest.mark.django_db
def test_reindex_mailbox(mock_es_client_index, test_mailbox, test_thread):
    """Test reindexing a specific mailbox."""

    # Call the function
    result = reindex_mailbox(str(test_mailbox.id))

    assert mock_es_client_index.index.call_count > 0

    # Verify result
    assert result["status"] == "success"
    assert result["mailbox"] == str(test_mailbox.id)


def test_search_threads_with_query(mock_es_client_search):
    """Test searching for threads with a query."""
    # Reset and setup mock response
    mock_es_client_search.search.return_value = {
        "hits": {
            "total": {"value": 1},
            "hits": [{"_source": {"thread_id": "123", "subject": "Test Subject"}}],
        }
    }

    # Call the function
    result = search_threads("test query", mailbox_ids=["mailbox-id"])

    # Verify ES client call
    assert mock_es_client_search.search.called
    # Check that the mailbox filter was applied
    call_args = mock_es_client_search.search.call_args[1]

    # Find the mailbox filter in the query
    mailbox_filter_found = False
    for filter_item in call_args["body"]["query"]["bool"]["filter"]:
        if "terms" in filter_item and "mailbox_ids" in filter_item["terms"]:
            mailbox_filter_found = True
            assert filter_item["terms"]["mailbox_ids"] == ["mailbox-id"]
    assert mailbox_filter_found, "Mailbox filter not found in query"

    # Verify result
    assert len(result["threads"]) == 1
    assert result["threads"][0]["id"] == "123"
    assert result["total"] == 1


def test_search_threads_pagination(mock_es_client_search):
    """Test pagination in thread search."""
    # Reset and setup mock response
    mock_es_client_search.search.return_value = {
        "hits": {
            "total": {"value": 30},
            "hits": [
                {"_source": {"thread_id": f"{i}", "subject": f"Subject {i}"}}
                for i in range(10)  # Return 10 results
            ],
        }
    }

    # Call with from_offset=10, size=10 (page 2)
    result = search_threads("test", from_offset=10, size=10)

    # Verify results
    assert len(result["threads"]) == 10
    assert result["total"] == 30
    assert result["from"] == 10
    assert result["size"] == 10

    # Verify pagination parameters were passed correctly
    call_args = mock_es_client_search.search.call_args[1]
    assert call_args["body"]["from"] == 10
    assert call_args["body"]["size"] == 10


@override_settings(OPENSEARCH_INDEX_THREADS=False)
def test_search_threads_disabled(mock_es_client_search):
    """Test searching threads when OpenSearch indexing is disabled."""

    # Call the function
    result = search_threads("test query")

    # Verify empty results
    assert len(result["threads"]) == 0
    assert result["total"] == 0

    # Verify ES client was not called
    mock_es_client_search.search.assert_not_called()
