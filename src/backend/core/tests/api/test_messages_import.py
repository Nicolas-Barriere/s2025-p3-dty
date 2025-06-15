"""Test messages import."""
# pylint: disable=redefined-outer-name, unused-argument, no-value-for-parameter

import datetime
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile

import pytest
from rest_framework.test import APIClient

from core import factories
from core.enums import MailboxRoleChoices
from core.models import Mailbox, MailDomain, Message

pytestmark = pytest.mark.django_db

IMPORT_FILE_URL = "/api/v1.0/import/file/"
IMPORT_IMAP_URL = "/api/v1.0/import/imap/"


@pytest.fixture
def user(db):
    """Create a user."""
    return factories.UserFactory()


@pytest.fixture
def api_client(user):
    """Create an API client."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def domain(db):
    """Create a test domain."""
    return MailDomain.objects.create(name="example.com")


@pytest.fixture
def mailbox(domain):
    """Create a test mailbox."""
    return Mailbox.objects.create(local_part="test", domain=domain)


@pytest.fixture
def eml_file_path():
    """Get the path to the EML file."""
    return "core/tests/resources/message.eml"


@pytest.fixture
def mbox_file_path():
    """Get the path to the MBOX file."""
    return "core/tests/resources/messages.mbox"


def test_import_eml_file(api_client, user, mailbox, eml_file_path):
    """Test import of EML file."""
    # add access to mailbox
    mailbox.accesses.create(user=user, role=MailboxRoleChoices.ADMIN)

    # Create a test EML file
    with open(eml_file_path, "rb") as f:
        response = api_client.post(
            IMPORT_FILE_URL,
            {"import_file": f, "recipient": str(mailbox.id)},
            format="multipart",
        )
    assert response.status_code == 202
    assert response.data["type"] == "eml"
    assert Message.objects.count() == 1
    message = Message.objects.first()
    assert message.subject == "Mon mail avec joli pj"
    assert message.attachments.count() == 1
    assert message.sender.email == "sender@example.com"
    assert message.recipients.get().contact.email == "recipient@example.com"
    assert message.sent_at == message.thread.messaged_at
    assert message.sent_at == datetime.datetime(
        2025, 5, 26, 20, 13, 44, tzinfo=datetime.timezone.utc
    )


def test_import_mbox_file(api_client, user, mailbox, mbox_file_path):
    """Test import of MBOX file."""
    # add access to mailbox
    mailbox.accesses.create(user=user, role=MailboxRoleChoices.ADMIN)

    with open(mbox_file_path, "rb") as f:
        response = api_client.post(
            IMPORT_FILE_URL,
            {"import_file": f, "recipient": str(mailbox.id)},
            format="multipart",
        )
    assert response.status_code == 202
    assert response.data["type"] == "mbox"
    # Verify messages were created
    assert Message.objects.count() == 3
    messages = Message.objects.order_by("created_at")

    # Check thread for each message
    assert messages[0].thread is not None
    assert messages[1].thread is not None
    assert messages[2].thread is not None
    assert messages[2].thread.messages.count() == 2
    assert messages[1].thread == messages[2].thread
    # Check created_at dates match between messages and threads
    assert messages[0].sent_at == messages[0].thread.messaged_at
    assert messages[2].sent_at == messages[1].thread.messaged_at
    assert messages[2].sent_at == (
        datetime.datetime(2025, 5, 26, 20, 18, 4, tzinfo=datetime.timezone.utc)
    )

    # Check messages
    assert messages[0].subject == "Mon mail avec joli pj"
    assert messages[0].attachments.count() == 1

    assert messages[1].subject == "Je t'envoie encore un message..."
    body1 = messages[1].get_parsed_field("textBody")[0]["content"]
    assert "Lorem ipsum dolor sit amet" in body1

    assert messages[2].subject == "Re: Je t'envoie encore un message..."
    body2 = messages[2].get_parsed_field("textBody")[0]["content"]
    assert "Yes !" in body2
    assert "Lorem ipsum dolor sit amet" in body2


def test_import_mbox_async(api_client, user, mailbox, mbox_file_path):
    """Test import of MBOX file asynchronously."""
    # add access to mailbox
    mailbox.accesses.create(user=user, role=MailboxRoleChoices.ADMIN)
    with patch("core.tasks.process_mbox_file_task.delay") as mock_task:
        mock_task.return_value.id = "fake-task-id"
        mock_task.return_value.status = "PENDING"
        with open(mbox_file_path, "rb") as f:
            response = api_client.post(
                IMPORT_FILE_URL,
                {"import_file": f, "recipient": str(mailbox.id)},
                format="multipart",
            )
            assert response.status_code == 202
            assert response.data["type"] == "mbox"
            assert mock_task.call_count == 1
            assert mock_task.call_args[0][1] == str(mailbox.id)


def test_import_file_no_access(api_client, domain, eml_file_path):
    """Test import of EML file without access to mailbox."""
    # Create a mailbox the user does NOT have access to
    mailbox = Mailbox.objects.create(local_part="noaccess", domain=domain)
    with open(eml_file_path, "rb") as f:
        response = api_client.post(
            IMPORT_FILE_URL,
            {"import_file": f, "recipient": str(mailbox.id)},
            format="multipart",
        )
    assert response.status_code == 403
    assert "access" in response.data["detail"]


def test_import_wrong_file_format(api_client, user, mailbox):
    """Test import of wrong file format."""
    # add access to mailbox
    mailbox.accesses.create(user=user, role=MailboxRoleChoices.ADMIN)

    # Create an invalid file (not EML or MBOX)
    wrong_file = SimpleUploadedFile(
        "test.pdf", b"Invalid file content", content_type="application/pdf"
    )
    response = api_client.post(
        IMPORT_FILE_URL,
        {"import_file": wrong_file, "recipient": str(mailbox.id)},
        format="multipart",
    )
    assert response.status_code == 400
    response_data = response.json()
    assert "import_file" in response_data
    assert len(response_data["import_file"]) == 1
    assert "Invalid file type" in response_data["import_file"][0]


def test_import_text_plain_wrong_extension(api_client, user, mailbox, mbox_file_path):
    """Test import of file with text/plain MIME type but wrong extension."""
    # add access to mailbox
    mailbox.accesses.create(user=user, role=MailboxRoleChoices.ADMIN)

    # Read the mbox file content
    with open(mbox_file_path, "rb") as f:
        mbox_content = f.read()

    # Create a file with text/plain MIME type but wrong extension
    wrong_file = SimpleUploadedFile(
        "test.txt",  # Wrong extension
        mbox_content,
        content_type="text/plain",
    )
    response = api_client.post(
        IMPORT_FILE_URL,
        {"import_file": wrong_file, "recipient": str(mailbox.id)},
        format="multipart",
    )
    assert response.status_code == 403
    response_data = response.json()
    assert "Invalid file" in response_data["detail"]


def test_import_text_plain_mime_type(api_client, user, mailbox, mbox_file_path):
    """Test import of MBOX file with text/plain MIME type."""
    # add access to mailbox
    mailbox.accesses.create(user=user, role=MailboxRoleChoices.ADMIN)

    # Read the mbox file content
    with open(mbox_file_path, "rb") as f:
        mbox_content = f.read()

    # Create a file with text/plain MIME type
    mbox_file = SimpleUploadedFile(
        "test.mbox",
        mbox_content,
        content_type="text/plain",
    )

    with patch("core.tasks.process_mbox_file_task.delay") as mock_task:
        mock_task.return_value.id = "fake-task-id"
        response = api_client.post(
            IMPORT_FILE_URL,
            {"import_file": mbox_file, "recipient": str(mailbox.id)},
            format="multipart",
        )

        assert response.status_code == 202
        assert response.data["type"] == "mbox"
        assert response.data["task_id"] == "fake-task-id"
        mock_task.assert_called_once()


def test_import_imap_task(api_client, user, mailbox):
    """Test import of IMAP messages."""
    mailbox.accesses.create(user=user, role=MailboxRoleChoices.ADMIN)
    with patch("core.tasks.import_imap_messages_task.delay") as mock_task:
        mock_task.return_value.id = "fake-task-id"
        data = {
            "recipient": str(mailbox.id),
            "imap_server": "imap.example.com",
            "imap_port": 993,
            "username": "test@example.com",
            "password": "password123",
            "use_ssl": True,
            "folder": "INBOX",
            "max_messages": 0,
        }
        response = api_client.post(IMPORT_IMAP_URL, data, format="json")
        assert response.status_code == 202
        assert response.data["task_id"] == "fake-task-id"
        assert response.data["type"] == "imap"
        mock_task.assert_called_once()


def test_import_imap(api_client, user, mailbox):
    """Test import of IMAP messages."""
    mailbox.accesses.create(user=user, role=MailboxRoleChoices.ADMIN)
    # Mock IMAP connection and responses
    with patch("imaplib.IMAP4_SSL") as mock_imap:
        mock_imap_instance = mock_imap.return_value
        mock_imap_instance.select.return_value = ("OK", [b"1"])
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
            ("OK", [(b"1", message1)]),
            ("OK", [(b"2", message2)]),
        ]

        data = {
            "recipient": str(mailbox.id),
            "imap_server": "imap.example.com",
            "imap_port": 993,
            "username": "test@example.com",
            "password": "password123",
            "use_ssl": True,
            "folder": "INBOX",
            "max_messages": 0,
        }
        response = api_client.post(IMPORT_IMAP_URL, data, format="json")
        assert response.status_code == 202
        assert response.data["type"] == "imap"
        assert Message.objects.count() == 2
        message1 = Message.objects.first()
        assert message1.subject == "Test Message 2"
        assert message1.sender.email == "sender@example.com"
        assert message1.recipients.get().contact.email == "recipient@example.com"
        assert message1.sent_at == message1.thread.messaged_at
        assert message1.sent_at == datetime.datetime(
            2025, 5, 26, 11, 0, 0, tzinfo=datetime.timezone.utc
        )
        message2 = Message.objects.last()
        assert message2.subject == "Test Message 1"
        assert message2.sender.email == "sender@example.com"
        assert message2.recipients.get().contact.email == "recipient@example.com"
        assert message2.sent_at == message2.thread.messaged_at
        assert message2.sent_at == datetime.datetime(
            2025, 5, 26, 10, 0, 0, tzinfo=datetime.timezone.utc
        )


def test_import_imap_no_access(api_client, domain):
    """Test import of IMAP messages without access to mailbox."""
    mailbox = Mailbox.objects.create(local_part="noaccess", domain=domain)
    data = {
        "recipient": str(mailbox.id),
        "imap_server": "imap.example.com",
        "imap_port": 993,
        "username": "test@example.com",
        "password": "password123",
        "use_ssl": True,
        "folder": "INBOX",
        "max_messages": 0,
    }
    response = api_client.post(IMPORT_IMAP_URL, data, format="json")
    assert response.status_code == 403
    assert "access" in response.data["detail"]


def test_import_mbox_file_no_extension(api_client, user, mailbox, mbox_file_path):
    """Test import of MBOX file without extension."""
    # add access to mailbox
    mailbox.accesses.create(user=user, role=MailboxRoleChoices.ADMIN)

    # Read the mbox file content
    with open(mbox_file_path, "rb") as f:
        mbox_content = f.read()

    # Create a file named "mbox" without extension
    mbox_file = SimpleUploadedFile(
        "mbox",  # filename without extension
        mbox_content,
        content_type="text/plain",
    )

    response = api_client.post(
        IMPORT_FILE_URL,
        {"import_file": mbox_file, "recipient": str(mailbox.id)},
        format="multipart",
    )

    assert response.status_code == 202
    assert response.data["type"] == "mbox"
    # Verify messages were created
    assert Message.objects.count() == 3
    messages = Message.objects.order_by("created_at")

    # Check thread for each message
    assert messages[0].thread is not None
    assert messages[1].thread is not None
    assert messages[2].thread is not None
    assert messages[2].thread.messages.count() == 2
    assert messages[1].thread == messages[2].thread

    # Check messages
    assert messages[0].subject == "Mon mail avec joli pj"
    assert messages[0].attachments.count() == 1

    assert messages[1].subject == "Je t'envoie encore un message..."
    body1 = messages[1].get_parsed_field("textBody")[0]["content"]
    assert "Lorem ipsum dolor sit amet" in body1

    assert messages[2].subject == "Re: Je t'envoie encore un message..."
    body2 = messages[2].get_parsed_field("textBody")[0]["content"]
    assert "Yes !" in body2
    assert "Lorem ipsum dolor sit amet" in body2
