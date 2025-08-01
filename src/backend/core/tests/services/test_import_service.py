"""Tests for the ImportService class."""

import datetime
from unittest.mock import MagicMock, patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest

import pytest

from core import factories
from core.enums import MailboxRoleChoices
from core.models import Mailbox, MailDomain, Message
from core.services.import_service import ImportService
from core.tasks import deliver_inbound_message, process_eml_file_task


@pytest.fixture
def user(db):
    """Create a user."""
    return factories.UserFactory()


@pytest.fixture
def admin_user(db):
    """Create a superuser for admin access."""
    return factories.UserFactory(
        email="admin@example.com",
        password="adminpass123",
        full_name="Admin User",
        is_superuser=True,
        is_staff=True,
    )


@pytest.fixture
def domain(db):
    """Create a test domain."""
    return MailDomain.objects.create(name="example.com")


@pytest.fixture
def mailbox(domain):
    """Create a test mailbox."""
    return Mailbox.objects.create(local_part="test", domain=domain)


@pytest.fixture
def mock_request():
    """Create a mock request object with messages framework support."""
    request = HttpRequest()
    request.user = None
    # Set up messages framework
    request.session = "session"
    messages = FallbackStorage(request)
    request._messages = messages
    return request


@pytest.fixture
def eml_file():
    """Get test eml file from test data."""
    with open("core/tests/resources/message.eml", "rb") as f:
        return SimpleUploadedFile("test.eml", f.read(), content_type="message/rfc822")


@pytest.fixture
def mbox_file_path():
    """Get test mbox file path from test data."""
    return "core/tests/resources/messages.mbox"


@pytest.fixture
def mbox_file(mbox_file_path):
    """Get test mbox file from test data."""
    with open(mbox_file_path, "rb") as f:
        return SimpleUploadedFile(
            "test.mbox", f.read(), content_type="application/mbox"
        )


@pytest.fixture
def blob_mbox(mbox_file, mailbox):
    """Create a blob from a file."""
    # Read the file content once
    file_content = mbox_file.read()
    return mailbox.create_blob(
        content=file_content,
        content_type=mbox_file.content_type,
    )


@pytest.fixture
def blob_eml(eml_file, mailbox):
    """Create a blob from a file."""
    # Read the file content once
    file_content = eml_file.read()
    return mailbox.create_blob(
        content=file_content,
        content_type=eml_file.content_type,
    )


@pytest.mark.django_db
def test_import_file_eml_by_superuser(admin_user, mailbox, blob_eml, mock_request):
    """Test successful EML file import for superuser."""
    with patch("core.tasks.process_eml_file_task.delay") as mock_task:
        mock_task.return_value.id = "fake-task-id"
        success, response_data = ImportService.import_file(
            file=blob_eml,
            recipient=mailbox,
            user=admin_user,
            request=mock_request,
        )

        assert success is True
        assert response_data["type"] == "eml"
        assert response_data["task_id"] == "fake-task-id"
        mock_task.assert_called_once()


@pytest.mark.django_db
def test_import_file_eml_by_superuser_sync(admin_user, mailbox, blob_eml):
    """Test importing an EML file by a superuser synchronously."""
    # Mock deliver_inbound_message to always succeed
    original_deliver = deliver_inbound_message

    def mock_deliver(recipient_email, parsed_email, raw_data, **kwargs):
        # Call the original function to create the message
        original_deliver(recipient_email, parsed_email, raw_data, **kwargs)
        return True

    with patch("core.tasks.deliver_inbound_message", side_effect=mock_deliver):
        # Create a mock task instance
        mock_task = MagicMock()
        mock_task.update_state = MagicMock()

        with patch.object(
            process_eml_file_task, "update_state", mock_task.update_state
        ):
            # Run the import
            task_result = process_eml_file_task(
                file_content=blob_eml.get_content(),
                recipient_id=str(mailbox.id),
            )

            # Verify task result structure
            assert isinstance(task_result, dict)
            assert "status" in task_result
            assert "result" in task_result
            assert "error" in task_result

            # Verify task result content
            assert task_result["status"] == "SUCCESS"
            assert (
                task_result["result"]["message_status"]
                == "Completed processing message"
            )
            assert task_result["result"]["type"] == "eml"
            assert task_result["result"]["total_messages"] == 1
            assert task_result["result"]["success_count"] == 1
            assert task_result["result"]["failure_count"] == 0
            assert task_result["result"]["current_message"] == 1
            assert task_result["error"] is None

            # Verify progress updates
            assert mock_task.update_state.call_count == 2  # 1 PROGRESS + 1 SUCCESS
            mock_task.update_state.assert_any_call(
                state="PROGRESS",
                meta={
                    "result": {
                        "message_status": "Processing message 1 of 1",
                        "total_messages": 1,
                        "success_count": 0,
                        "failure_count": 0,
                        "type": "eml",
                        "current_message": 1,
                    },
                    "error": None,
                },
            )

            # Verify success update
            mock_task.update_state.assert_called_with(
                state="SUCCESS",
                meta={
                    "result": task_result["result"],
                    "error": None,
                },
            )

            # Verify message was created
            assert Message.objects.count() == 1
            message = Message.objects.first()
            assert message.subject == "Mon mail avec joli pj"
            assert message.sender.email == "sender@example.com"
            assert message.recipients.count() == 1
            assert message.recipients.first().contact.email == "recipient@example.com"


@pytest.mark.django_db
def test_import_file_eml_by_user_with_access_task(
    user, mailbox, blob_eml, mock_request
):
    """Test successful EML file import by user with access on mailbox."""
    # Add access to mailbox
    mailbox.accesses.create(user=user, role=MailboxRoleChoices.ADMIN)

    with patch("core.tasks.process_eml_file_task.delay") as mock_task:
        mock_task.return_value.id = "fake-task-id"
        success, response_data = ImportService.import_file(
            file=blob_eml,
            recipient=mailbox,
            user=user,
            request=mock_request,
        )

        assert success is True
        assert response_data["type"] == "eml"
        assert response_data["task_id"] == "fake-task-id"
        mock_task.assert_called_once()


@pytest.mark.django_db
def test_import_file_eml_by_user_with_access_sync(
    user, mailbox, blob_eml, mock_request
):
    """Test importing an EML file by a user with access synchronously."""
    # Add access to mailbox
    mailbox.accesses.create(user=user, role=MailboxRoleChoices.ADMIN)

    # Mock deliver_inbound_message to always succeed
    original_deliver = deliver_inbound_message

    def mock_deliver(recipient_email, parsed_email, raw_data, **kwargs):
        # Call the original function to create the message
        original_deliver(recipient_email, parsed_email, raw_data, **kwargs)
        return True

    with patch("core.tasks.deliver_inbound_message", side_effect=mock_deliver):
        # Create a mock task instance
        mock_task = MagicMock()
        mock_task.update_state = MagicMock()

        with patch.object(
            process_eml_file_task, "update_state", mock_task.update_state
        ):
            # Run the import
            task_result = process_eml_file_task(
                file_content=blob_eml.get_content(),
                recipient_id=str(mailbox.id),
            )

            # Verify task result structure
            assert isinstance(task_result, dict)
            assert "status" in task_result
            assert "result" in task_result
            assert "error" in task_result

            # Verify task result content
            assert task_result["status"] == "SUCCESS"
            assert (
                task_result["result"]["message_status"]
                == "Completed processing message"
            )
            assert task_result["result"]["type"] == "eml"
            assert task_result["result"]["total_messages"] == 1
            assert task_result["result"]["success_count"] == 1
            assert task_result["result"]["failure_count"] == 0
            assert task_result["result"]["current_message"] == 1
            assert task_result["error"] is None

            # Verify progress updates
            assert mock_task.update_state.call_count == 2  # 1 PROGRESS + 1 SUCCESS
            mock_task.update_state.assert_any_call(
                state="PROGRESS",
                meta={
                    "result": {
                        "message_status": "Processing message 1 of 1",
                        "total_messages": 1,
                        "success_count": 0,
                        "failure_count": 0,
                        "type": "eml",
                        "current_message": 1,
                    },
                    "error": None,
                },
            )

            # Verify success update
            mock_task.update_state.assert_called_with(
                state="SUCCESS",
                meta={
                    "result": task_result["result"],
                    "error": None,
                },
            )

            # Verify message was created
            assert Message.objects.count() == 1
            message = Message.objects.first()
            assert message.subject == "Mon mail avec joli pj"
            assert message.sender.email == "sender@example.com"
            assert message.recipients.count() == 1
            assert message.recipients.first().contact.email == "recipient@example.com"


@pytest.mark.django_db
def test_import_file_mbox_by_superuser_task(
    admin_user, mailbox, blob_mbox, mock_request
):
    """Test successful MBOX file import by superuser."""

    with patch("core.tasks.process_mbox_file_task.delay") as mock_task:
        mock_task.return_value.id = "fake-task-id"
        success, response_data = ImportService.import_file(
            file=blob_mbox,
            recipient=mailbox,
            user=admin_user,
            request=mock_request,
        )

        assert success is True
        assert response_data["type"] == "mbox"
        assert response_data["task_id"] == "fake-task-id"
        mock_task.assert_called_once()


@pytest.mark.django_db
def test_import_file_mbox_by_user_with_access_task(
    user, mailbox, blob_mbox, mock_request
):
    """Test successful MBOX file import by user with access on mailbox."""
    # Add access to mailbox
    mailbox.accesses.create(user=user, role=MailboxRoleChoices.ADMIN)

    with patch("core.tasks.process_mbox_file_task.delay") as mock_task:
        mock_task.return_value.id = "fake-task-id"
        success, response_data = ImportService.import_file(
            file=blob_mbox,
            recipient=mailbox,
            user=user,
            request=mock_request,
        )

        assert success is True
        assert response_data["type"] == "mbox"
        assert response_data["task_id"] == "fake-task-id"
        mock_task.assert_called_once()


@pytest.mark.django_db
def test_import_file_mbox_by_superuser_db_creation(
    admin_user, mailbox, blob_mbox, mock_request
):
    """Test file import for a superuser"""
    success, response_data = ImportService.import_file(
        file=blob_mbox,
        recipient=mailbox,
        user=admin_user,
        request=mock_request,
    )

    assert success is True
    assert response_data["type"] == "mbox"
    assert Message.objects.count() == 3
    message = Message.objects.last()
    assert message.subject == "Mon mail avec joli pj"
    assert message.has_attachments is True
    assert message.sender.email == "julie.sender@example.com"
    assert message.recipients.get().contact.email == "jean.recipient@example.com"
    assert message.sent_at == message.thread.messaged_at
    assert message.sent_at == datetime.datetime(
        2025, 5, 26, 20, 13, 44, tzinfo=datetime.timezone.utc
    )


def test_import_file_no_access(user, domain, blob_eml, mock_request):
    """Test file import without mailbox access."""
    # Create a mailbox the user does NOT have access to
    mailbox = Mailbox.objects.create(local_part="noaccess", domain=domain)

    success, response_data = ImportService.import_file(
        file=blob_eml,
        recipient=mailbox,
        user=user,
        request=mock_request,
    )

    assert success is False
    assert "You do not have access to this mailbox" in response_data["detail"]
    assert Message.objects.count() == 0


@pytest.mark.django_db
def test_import_file_invalid_file(admin_user, mailbox, mock_request):
    """Test import with an invalid file."""
    # Create an invalid file (not EML or MBOX)
    invalid_content = b"Invalid file content"
    invalid_file = mailbox.create_blob(
        content=invalid_content,
        content_type="application/pdf",  # Invalid MIME type for email import
    )

    with patch("core.tasks.process_eml_file_task.delay") as mock_task:
        # The task should not be called for invalid files
        mock_task.assert_not_called()

        success, response_data = ImportService.import_file(
            file=invalid_file,
            recipient=mailbox,
            user=admin_user,
            request=mock_request,
        )

        assert success is False
        assert "detail" in response_data
        assert "Invalid file format" in response_data["detail"]
        assert Message.objects.count() == 0


@pytest.mark.django_db
def test_import_file_text_plain_mime_type(
    admin_user, mailbox, mock_request, mbox_file_path
):
    """Test import of MBOX file with text/plain MIME type."""
    # Read the mbox file content
    with open(mbox_file_path, "rb") as f:
        mbox_content = f.read()

    # Create a file with text/plain MIME type
    blob_mbox = mailbox.create_blob(
        content=mbox_content,
        content_type="text/plain",
    )

    with patch("core.tasks.process_mbox_file_task.delay") as mock_task:
        # The task should be called for text/plain files (they are now accepted as MBOX)
        mock_task.return_value.id = "fake-task-id"
        success, response_data = ImportService.import_file(
            file=blob_mbox,
            recipient=mailbox,
            user=admin_user,
            request=mock_request,
        )

        assert success is True
        assert response_data["type"] == "mbox"
        assert response_data["task_id"] == "fake-task-id"
        mock_task.assert_called_once()


def test_import_imap_by_superuser(admin_user, mailbox, mock_request):
    """Test successful IMAP import."""
    with patch("core.tasks.import_imap_messages_task.delay") as mock_task:
        mock_task.return_value.id = "fake-task-id"
        success, response_data = ImportService.import_imap(
            imap_server="imap.example.com",
            imap_port=993,
            username="test@example.com",
            password="password123",
            recipient=mailbox,
            user=admin_user,
            use_ssl=True,
            request=mock_request,
        )

        assert success is True
        assert response_data["type"] == "imap"
        assert response_data["task_id"] == "fake-task-id"
        mock_task.assert_called_once()


@pytest.mark.parametrize(
    "role",
    [
        MailboxRoleChoices.ADMIN,
        MailboxRoleChoices.EDITOR,
        MailboxRoleChoices.SENDER,
    ],
)
def test_import_imap_by_user_with_access(user, mailbox, mock_request, role):
    """Test successful IMAP import by user with access on mailbox."""
    # Add access to mailbox
    mailbox.accesses.create(user=user, role=role)

    with patch("core.tasks.import_imap_messages_task.delay") as mock_task:
        mock_task.return_value.id = "fake-task-id"
        success, response_data = ImportService.import_imap(
            imap_server="imap.example.com",
            imap_port=993,
            username="test@example.com",
            password="password123",
            recipient=mailbox,
            user=user,
            use_ssl=True,
            request=mock_request,
        )

        assert success is True
        assert response_data["type"] == "imap"
        assert response_data["task_id"] == "fake-task-id"
        mock_task.assert_called_once()


def test_import_imap_no_access(user, domain, mock_request):
    """Test IMAP import without mailbox access."""
    # Create a mailbox the user does NOT have access to
    mailbox = Mailbox.objects.create(local_part="noaccess", domain=domain)

    success, response_data = ImportService.import_imap(
        imap_server="imap.example.com",
        imap_port=993,
        username="test@example.com",
        password="password123",
        recipient=mailbox,
        user=user,
        use_ssl=True,
        request=mock_request,
    )

    assert success is False
    assert "access" in response_data["detail"]


def test_import_imap_task_error(admin_user, mailbox, mock_request):
    """Test IMAP import with task error."""
    # Add access to mailbox
    mailbox.accesses.create(user=admin_user, role=MailboxRoleChoices.ADMIN)

    with patch("core.tasks.import_imap_messages_task.delay") as mock_task:
        mock_task.side_effect = Exception("Task error")
        success, response_data = ImportService.import_imap(
            imap_server="imap.example.com",
            imap_port=993,
            username="test@example.com",
            password="password123",
            recipient=mailbox,
            user=admin_user,
            use_ssl=True,
            request=mock_request,
        )

        assert success is False
        assert "detail" in response_data
        assert "Task error" in response_data["detail"]


def test_import_imap_messages_by_superuser(admin_user, mailbox, mock_request):
    """Test importing messages from IMAP server by superuser."""

    # Mock IMAP connection and responses
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap_instance = mock_imap.return_value

        # Mock login
        mock_imap_instance.login.return_value = ("OK", [b"Logged in"])

        # Mock list folders - return INBOX folder
        mock_imap_instance.list.return_value = (
            "OK",
            [b'(\\HasNoChildren) "/" "INBOX"'],
        )

        # Mock select folder
        mock_imap_instance.select.return_value = ("OK", [b"1"])

        # Mock search for messages
        mock_imap_instance.search.return_value = ("OK", [b"1 2"])

        # Mock 2 messages with proper IMAP response format
        message1 = b"""From: sender@example.com
To: recipient@example.com
Subject: Test Message 1
Date: Mon, 26 May 2025 10:00:00 +0000

Test message body 1"""

        message2 = b"""From: sender@example.com 
To: recipient@example.com
Subject: Test Message 2
Date: Mon, 26 May 2025 11:00:00 +0000

Test message body 2"""

        # Mock fetch responses with proper IMAP format including flags
        mock_imap_instance.fetch.side_effect = [
            # First message: flags + content
            ("OK", [(b"1 (FLAGS (\\Seen \\Answered))", message1)]),
            # Second message: flags + content
            ("OK", [(b"2 (FLAGS (\\Seen))", message2)]),
        ]

        success, response_data = ImportService.import_imap(
            imap_server="imap.example.com",
            imap_port=993,
            username="test@example.com",
            password="password123",
            recipient=mailbox,
            user=admin_user,
            use_ssl=True,
            request=mock_request,
        )

        assert success is True
        assert response_data["type"] == "imap"
        assert "task_id" in response_data

        # Verify IMAP calls
        mock_imap_instance.login.assert_called_once_with(
            "test@example.com", "password123"
        )
        # The select method may be called multiple times with different folder name variations
        assert mock_imap_instance.select.call_count >= 1
        # Check that at least one call was made with "INBOX"
        select_calls = [call[0][0] for call in mock_imap_instance.select.call_args_list]
        assert "INBOX" in select_calls
        # The search method may be called multiple times with different criteria
        assert mock_imap_instance.search.call_count >= 1
        # Check that at least one call was made with "ALL"
        search_calls = [call[0][1] for call in mock_imap_instance.search.call_args_list]
        assert "ALL" in search_calls
        assert mock_imap_instance.fetch.call_count == 2
        assert Message.objects.count() == 2
        message = Message.objects.last()
        assert message.subject == "Test Message 1"
        assert message.sender.email == "sender@example.com"
        assert message.recipients.get().contact.email == "recipient@example.com"
        assert message.sent_at == datetime.datetime(
            2025, 5, 26, 10, 0, 0, tzinfo=datetime.timezone.utc
        )


def test_import_imap_messages_user_with_access(user, mailbox, mock_request):
    """Test importing messages from IMAP server by user with access on mailbox."""
    # Add access to mailbox
    mailbox.accesses.create(user=user, role=MailboxRoleChoices.ADMIN)

    # Mock IMAP connection and responses
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap_instance = mock_imap.return_value

        # Mock login
        mock_imap_instance.login.return_value = ("OK", [b"Logged in"])

        # Mock list folders - return INBOX folder
        mock_imap_instance.list.return_value = (
            "OK",
            [b'(\\HasNoChildren) "/" "INBOX"'],
        )

        # Mock select folder
        mock_imap_instance.select.return_value = ("OK", [b"1"])

        # Mock search for messages
        mock_imap_instance.search.return_value = ("OK", [b"1 2"])

        # Mock 2 messages
        message1 = b"""From: sender@example.com
To: recipient@example.com
Subject: Test Message 1
Date: Mon, 26 May 2025 10:00:00 +0000

Test message body 1"""

        message2 = b"""From: sender@example.com 
To: recipient@example.com
Subject: Test Message 2
Date: Mon, 26 May 2025 11:00:00 +0000

Test message body 2"""

        mock_imap_instance.fetch.side_effect = [
            # First message: flags + content
            ("OK", [(b"1 (FLAGS (\\Seen \\Answered))", message1)]),
            # Second message: flags + content
            ("OK", [(b"2 (FLAGS (\\Seen))", message2)]),
        ]

        success, response_data = ImportService.import_imap(
            imap_server="imap.example.com",
            imap_port=993,
            username="test@example.com",
            password="password123",
            recipient=mailbox,
            user=user,
            use_ssl=True,
            request=mock_request,
        )

        assert success is True
        assert response_data["type"] == "imap"
        assert "task_id" in response_data

        # Verify IMAP calls
        mock_imap_instance.login.assert_called_once_with(
            "test@example.com", "password123"
        )
        # The select method may be called multiple times with different folder name variations
        assert mock_imap_instance.select.call_count >= 1
        # Check that at least one call was made with "INBOX"
        select_calls = [call[0][0] for call in mock_imap_instance.select.call_args_list]
        assert "INBOX" in select_calls
        # The search method may be called multiple times with different criteria
        assert mock_imap_instance.search.call_count >= 1
        # Check that at least one call was made with "ALL"
        search_calls = [call[0][1] for call in mock_imap_instance.search.call_args_list]
        assert "ALL" in search_calls
        assert Message.objects.count() == 2
        message = Message.objects.last()
        assert message.subject == "Test Message 1"
        assert message.sender.email == "sender@example.com"
        assert message.recipients.get().contact.email == "recipient@example.com"
        assert message.sent_at == datetime.datetime(
            2025, 5, 26, 10, 0, 0, tzinfo=datetime.timezone.utc
        )
