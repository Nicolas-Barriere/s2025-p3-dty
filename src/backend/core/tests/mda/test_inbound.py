"""Tests for the core.mda.inbound module."""

from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone

import pytest

from core import enums, factories, models
from core.mda.inbound import deliver_inbound_message, find_thread_for_inbound_message


@pytest.mark.django_db
class TestFindThread:
    """Unit tests for the find_thread_for_inbound_message helper."""

    mailbox = None

    @pytest.fixture(autouse=True)
    def setup_mailbox(self):
        """Create a mailbox for testing thread finding."""
        self.mailbox = factories.MailboxFactory()

    @pytest.mark.parametrize(
        "role",
        [
            enums.ThreadAccessRoleChoices.EDITOR,
            enums.ThreadAccessRoleChoices.VIEWER,
        ],
    )
    def test_find_by_references_and_subject(self, role):
        """Thread found via References header and matching normalized subject."""
        initial_mime_id = "original.123@example.com"
        initial_subject = "Original Thread Subject"
        initial_thread = factories.ThreadFactory(subject=initial_subject)
        factories.ThreadAccessFactory(
            mailbox=self.mailbox,
            thread=initial_thread,
            role=role,
        )
        factories.MessageFactory(
            thread=initial_thread, mime_id=initial_mime_id, subject=initial_subject
        )

        # Parsed email data for the incoming reply
        parsed_reply = {
            "subject": f"Re: {initial_subject}",
            "headers": {
                "references": f"<other.ref@example.com> <{initial_mime_id}>",
            },
            "from": {"email": "replier@a.com"},
        }

        found_thread = find_thread_for_inbound_message(parsed_reply, self.mailbox)
        assert found_thread == initial_thread

    @pytest.mark.parametrize(
        "role",
        [
            enums.ThreadAccessRoleChoices.EDITOR,
            enums.ThreadAccessRoleChoices.VIEWER,
        ],
    )
    def test_find_by_in_reply_to_and_subject(self, role):
        """Thread found via In-Reply-To header and matching normalized subject."""
        initial_subject = "Another Subject"
        initial_mime_id = "original.456@example.com"
        initial_thread = factories.ThreadFactory(subject=initial_subject)
        factories.ThreadAccessFactory(
            mailbox=self.mailbox,
            thread=initial_thread,
            role=role,
        )
        factories.MessageFactory(
            thread=initial_thread, mime_id=initial_mime_id, subject=initial_subject
        )

        parsed_reply = {
            "subject": f"Fwd: {initial_subject}",  # Different prefix, should still match
            "in_reply_to": f"{initial_mime_id}",
            "from": {"email": "replier@a.com"},
        }

        found_thread = find_thread_for_inbound_message(parsed_reply, self.mailbox)
        assert found_thread == initial_thread

    @pytest.mark.parametrize(
        "role",
        [
            enums.ThreadAccessRoleChoices.EDITOR,
            enums.ThreadAccessRoleChoices.VIEWER,
        ],
    )
    def test_find_fallback_no_subject_match(self, role):
        """Thread found via References header, falling back when subjects don't normalize."""
        initial_subject = "Meeting Request"
        initial_mime_id = "meeting.abc@example.com"
        initial_thread = factories.ThreadFactory(subject=initial_subject)
        factories.ThreadAccessFactory(
            mailbox=self.mailbox,
            thread=initial_thread,
            role=role,
        )
        factories.MessageFactory(
            thread=initial_thread, mime_id=initial_mime_id, subject=initial_subject
        )

        # Reply has reference, but completely different subject
        parsed_reply = {
            "subject": "Totally Unrelated Topic",
            "headers": {
                "references": f"<{initial_mime_id}>",
            },
            "from": {"email": "replier@a.com"},
        }

        # Create a new thread
        found_thread = find_thread_for_inbound_message(parsed_reply, self.mailbox)
        assert found_thread is None

    @pytest.mark.parametrize(
        "role",
        [
            enums.ThreadAccessRoleChoices.EDITOR,
            enums.ThreadAccessRoleChoices.VIEWER,
        ],
    )
    def test_no_match_returns_none(self, role):
        """No thread found if no matching references exist."""
        initial_thread = factories.ThreadFactory(
            subject="Some Thread"
        )  # Existing thread
        factories.ThreadAccessFactory(
            mailbox=self.mailbox,
            thread=initial_thread,
            role=role,
        )

        parsed_reply = {
            "subject": "Re: Some Thread",
            "headers": {
                "references": "<nonexistent.ref@example.com>",
            },
            "in_reply_to": "another.nonexistent@example.com",
            "from": {"email": "replier@a.com"},
        }

        found_thread = find_thread_for_inbound_message(parsed_reply, self.mailbox)
        assert found_thread is None

    @pytest.mark.parametrize(
        "role",
        [
            enums.ThreadAccessRoleChoices.EDITOR,
            enums.ThreadAccessRoleChoices.VIEWER,
        ],
    )
    def test_reference_in_different_mailbox(self, role):
        """No thread found if referenced message is in a different mailbox."""
        initial_subject = "My Mailbox Subject"
        initial_mime_id = "mine.xyz@example.com"
        initial_thread = factories.ThreadFactory(subject=initial_subject)
        factories.ThreadAccessFactory(
            mailbox=self.mailbox,
            thread=initial_thread,
            role=role,
        )
        factories.MessageFactory(
            thread=initial_thread, mime_id=initial_mime_id, subject=initial_subject
        )

        # Create a message in another mailbox with the same mime_id (unlikely but for test)
        other_mailbox = factories.MailboxFactory()
        other_thread = factories.ThreadFactory(subject="Other Subject")
        factories.ThreadAccessFactory(
            mailbox=other_mailbox,
            thread=other_thread,
            role=role,
        )
        factories.MessageFactory(
            thread=other_thread, mime_id=initial_mime_id, subject="Other Subject"
        )

        parsed_reply = {
            "subject": f"Re: {initial_subject}",
            "headers": {
                "references": f"<{initial_mime_id}>",
            },
            "from": {"email": "replier@a.com"},
        }

        # Should find the thread in *our* mailbox
        found_thread = find_thread_for_inbound_message(parsed_reply, self.mailbox)
        assert found_thread == initial_thread

    @pytest.mark.parametrize(
        "role",
        [
            enums.ThreadAccessRoleChoices.EDITOR,
            enums.ThreadAccessRoleChoices.VIEWER,
        ],
    )
    def test_no_references_returns_none(self, role):
        """No thread found if the incoming email has no reference headers."""
        initial_thread = factories.ThreadFactory(subject="Some Thread")
        factories.ThreadAccessFactory(
            mailbox=self.mailbox,
            thread=initial_thread,
            role=role,
        )

        parsed_new_email = {
            "subject": "Brand New Topic",
            # No In-Reply-To or References
            "from": {"email": "new@a.com"},
        }
        found_thread = find_thread_for_inbound_message(parsed_new_email, self.mailbox)
        assert found_thread is None


@pytest.mark.django_db
class TestDeliverInboundMessage:
    """Unit tests for the deliver_inbound_message function."""

    @pytest.fixture
    def sample_parsed_email(self):
        """Sample parsed email data for testing delivery."""
        return {
            "subject": "Delivery Test Subject",
            "from": {"name": "Test Sender", "email": "sender@test.com"},
            "to": [{"name": "Recipient Name", "email": "recipient@deliver.test"}],
            "cc": [],
            "bcc": [],
            "textBody": [{"content": "Test body content."}],
            "message_id": "test.delivery.1@example.com",
            "date": timezone.now(),
        }

    @pytest.fixture
    def raw_email_data(self):
        """Raw email data placeholder."""
        return b"Raw email data placeholder"

    @pytest.fixture
    def target_mailbox(self):
        """Create a mailbox for testing delivery."""
        domain = factories.MailDomainFactory(name="deliver.test")
        return factories.MailboxFactory(local_part="recipient", domain=domain)

    @patch("core.mda.inbound.find_thread_for_inbound_message")
    def test_basic_delivery_new_thread(
        self, mock_find_thread, target_mailbox, sample_parsed_email, raw_email_data
    ):
        """Test successful delivery creating a new thread and contacts."""
        mock_find_thread.return_value = None  # Simulate no existing thread found
        recipient_addr = f"{target_mailbox.local_part}@{target_mailbox.domain.name}"

        assert models.Thread.objects.count() == 0
        assert models.Contact.objects.count() == 0
        assert models.Message.objects.count() == 0

        success = deliver_inbound_message(
            recipient_addr, sample_parsed_email, raw_email_data
        )

        assert success is True
        mock_find_thread.assert_called_once_with(sample_parsed_email, target_mailbox)

        assert models.Thread.objects.count() == 1
        assert models.Message.objects.count() == 1
        # Sender + Recipient contacts created associated with the target mailbox
        assert models.Contact.objects.count() == 2

        thread = models.Thread.objects.first()
        assert thread.accesses.first().mailbox == target_mailbox
        assert thread.subject == sample_parsed_email["subject"]
        assert thread.has_unread is True
        assert thread.snippet == "Test body content."

        message = models.Message.objects.first()
        assert message.thread == thread
        assert message.subject == sample_parsed_email["subject"]
        assert message.sender.email == "sender@test.com"
        assert message.sender.name == "Test Sender"
        assert message.sender.mailbox == target_mailbox
        assert message.blob.get_content() == raw_email_data
        assert message.mime_id == sample_parsed_email["message_id"]
        assert message.read_at is None

        assert message.recipients.count() == 1
        msg_recipient = message.recipients.first()
        assert msg_recipient.type == models.MessageRecipientTypeChoices.TO
        assert msg_recipient.contact.email == "recipient@deliver.test"
        assert msg_recipient.contact.name == "Recipient Name"
        assert msg_recipient.contact.mailbox == target_mailbox

    @pytest.mark.parametrize(
        "role",
        [
            enums.ThreadAccessRoleChoices.EDITOR,
            enums.ThreadAccessRoleChoices.VIEWER,
        ],
    )
    @patch("core.mda.inbound.find_thread_for_inbound_message")
    def test_basic_delivery_existing_thread(
        self,
        mock_find_thread,
        target_mailbox,
        sample_parsed_email,
        raw_email_data,
        role,
    ):  # pylint: disable=too-many-positional-arguments
        """Test successful delivery adding message to an existing thread."""
        existing_thread = factories.ThreadFactory()
        factories.ThreadAccessFactory(
            mailbox=target_mailbox,
            thread=existing_thread,
            role=role,
        )
        mock_find_thread.return_value = existing_thread
        recipient_addr = f"{target_mailbox.local_part}@{target_mailbox.domain.name}"

        assert models.Thread.objects.count() == 1
        assert models.Message.objects.count() == 0

        success = deliver_inbound_message(
            recipient_addr, sample_parsed_email, raw_email_data
        )

        assert success is True
        mock_find_thread.assert_called_once_with(sample_parsed_email, target_mailbox)
        assert models.Thread.objects.count() == 1  # No new thread
        assert models.Message.objects.count() == 1
        message = models.Message.objects.first()
        assert message.thread == existing_thread
        # Ensure thread is marked unread again
        existing_thread.refresh_from_db()
        assert existing_thread.has_unread is True

    @override_settings(MESSAGES_ACCEPT_ALL_EMAILS=True)
    def test_mailbox_creation_enabled(self, sample_parsed_email, raw_email_data):
        """Test mailbox is created automatically when MESSAGES_ACCEPT_ALL_EMAILS is True."""
        recipient_addr = "newuser@autocreate.test"
        assert not models.Mailbox.objects.filter(
            local_part="newuser", domain__name="autocreate.test"
        ).exists()

        success = deliver_inbound_message(
            recipient_addr, sample_parsed_email, raw_email_data
        )

        assert success is True
        assert models.Mailbox.objects.filter(
            local_part="newuser", domain__name="autocreate.test"
        ).exists()
        assert models.Message.objects.count() == 1  # Check message was delivered

    @override_settings(
        MESSAGES_ACCEPT_ALL_EMAILS=False, MESSAGES_TESTDOMAIN="something.else"
    )
    def test_mailbox_creation_disabled(self, sample_parsed_email, raw_email_data):
        """Test delivery fails if mailbox doesn't exist and auto-creation is off."""
        recipient_addr = "nonexistent@disabled.test"
        assert not models.Mailbox.objects.filter(
            local_part="nonexistent", domain__name="disabled.test"
        ).exists()

        success = deliver_inbound_message(
            recipient_addr, sample_parsed_email, raw_email_data
        )

        assert success is False
        assert not models.Mailbox.objects.filter(
            local_part="nonexistent", domain__name="disabled.test"
        ).exists()
        assert models.Message.objects.count() == 0

    def test_contact_creation(
        self, target_mailbox, sample_parsed_email, raw_email_data
    ):
        """Test that sender and recipient contacts are created correctly."""
        recipient_addr = f"{target_mailbox.local_part}@{target_mailbox.domain.name}"
        sample_parsed_email["to"] = [{"name": "Test Recip", "email": recipient_addr}]
        sample_parsed_email["cc"] = [{"name": "CC Contact", "email": "cc@example.com"}]
        sender_email = sample_parsed_email["from"]["email"]

        assert not models.Contact.objects.filter(
            email=sender_email, mailbox=target_mailbox
        ).exists()
        assert not models.Contact.objects.filter(
            email=recipient_addr, mailbox=target_mailbox
        ).exists()
        assert not models.Contact.objects.filter(
            email="cc@example.com", mailbox=target_mailbox
        ).exists()

        success = deliver_inbound_message(
            recipient_addr, sample_parsed_email, raw_email_data
        )

        assert success is True
        assert models.Contact.objects.filter(
            email=sender_email, mailbox=target_mailbox
        ).exists()
        assert models.Contact.objects.filter(
            email=recipient_addr, mailbox=target_mailbox
        ).exists()
        assert models.Contact.objects.filter(
            email="cc@example.com", mailbox=target_mailbox
        ).exists()
        assert models.MessageRecipient.objects.count() == 2  # TO and CC

    def test_invalid_sender_email_validation(
        self, target_mailbox, sample_parsed_email, raw_email_data
    ):
        """Test delivery uses fallback sender if From address is invalid."""
        recipient_addr = f"{target_mailbox.local_part}@{target_mailbox.domain.name}"
        sample_parsed_email["from"] = {
            "name": "Invalid Sender",
            "email": "invalid-email-format",
        }

        success = deliver_inbound_message(
            recipient_addr, sample_parsed_email, raw_email_data
        )

        assert success is True  # Should still succeed using fallback
        message = models.Message.objects.first()
        assert message is not None
        fallback_sender_email = f"invalid-sender@{target_mailbox.domain.name}"
        assert message.sender.email == fallback_sender_email
        assert message.sender.name == "Invalid Sender Address"
        assert models.Contact.objects.filter(
            email=fallback_sender_email, mailbox=target_mailbox
        ).exists()

    def test_no_sender_email(self, target_mailbox, sample_parsed_email, raw_email_data):
        """Test delivery uses fallback sender if From header is missing."""
        recipient_addr = f"{target_mailbox.local_part}@{target_mailbox.domain.name}"
        del sample_parsed_email["from"]  # Remove From header

        success = deliver_inbound_message(
            recipient_addr, sample_parsed_email, raw_email_data
        )

        assert success is True
        message = models.Message.objects.first()
        assert message is not None
        fallback_sender_email = f"unknown-sender@{target_mailbox.domain.name}"
        assert message.sender.email == fallback_sender_email
        assert message.sender.name == "Unknown Sender"
        assert models.Contact.objects.filter(
            email=fallback_sender_email, mailbox=target_mailbox
        ).exists()

    def test_invalid_recipient_email_skipped(
        self, target_mailbox, sample_parsed_email, raw_email_data
    ):
        """Test that recipients with invalid email formats are skipped."""
        recipient_addr = f"{target_mailbox.local_part}@{target_mailbox.domain.name}"
        sample_parsed_email["to"] = [
            {"name": "Valid Recip", "email": recipient_addr},
            {"name": "Invalid Recip", "email": "bad-email"},  # Invalid
        ]
        sample_parsed_email["cc"] = [
            {"name": "Another Invalid", "email": "@no-localpart.com"},  # Invalid
        ]

        success = deliver_inbound_message(
            recipient_addr, sample_parsed_email, raw_email_data
        )

        assert success is True  # Delivery succeeds overall
        message = models.Message.objects.first()
        assert message is not None
        # Only the valid recipient should have a MessageRecipient link
        assert message.recipients.count() == 1
        assert message.recipients.first().contact.email == recipient_addr
        # Check contacts were not created for invalid emails
        assert not models.Contact.objects.filter(email="bad-email").exists()
        assert not models.Contact.objects.filter(email="@no-localpart.com").exists()

    def test_email_exchange_single_thread(self):
        """Test a multi-step email exchange results in one thread per mailbox."""
        # Setup mailboxes
        domain = factories.MailDomainFactory(name="exchange.test")
        mailbox1 = factories.MailboxFactory(local_part="user1", domain=domain)
        mailbox2 = factories.MailboxFactory(local_part="user2", domain=domain)
        addr1 = str(mailbox1)
        addr2 = str(mailbox2)

        # 1. user1 -> user2
        subject = "Conversation Starter"
        parsed_email_1 = {
            "subject": subject,
            "from": {"name": "User One", "email": addr1},
            "to": [{"name": "User Two", "email": addr2}],
            "textBody": [{"content": "Hello User Two!"}],
            "message_id": "msg1.part1@exchange.test",
            "date": timezone.now(),
        }
        raw_email_1 = b"Raw for message 1"

        success1 = deliver_inbound_message(addr2, parsed_email_1, raw_email_1)
        assert success1 is True
        assert models.Thread.objects.filter(accesses__mailbox=mailbox1).count() == 0
        assert models.Thread.objects.filter(accesses__mailbox=mailbox2).count() == 1
        thread2 = models.Thread.objects.get(accesses__mailbox=mailbox2)
        assert thread2.messages.count() == 1
        assert thread2.subject == subject
        message1 = thread2.messages.first()
        assert message1.mime_id == parsed_email_1["message_id"]

        # 2. user2 -> user1 (Reply)
        parsed_email_2 = {
            "subject": f"Re: {subject}",
            "from": {"name": "User Two", "email": addr2},
            "to": [{"name": "User One", "email": addr1}],
            "textBody": [{"content": "Hi User One, thanks!"}],
            "message_id": "msg2.part2.reply@exchange.test",
            "in_reply_to": message1.mime_id,  # Link to previous message
            "headers": {"references": f"<{message1.mime_id}>"},
            "date": timezone.now(),
        }
        raw_email_2 = b"Raw for message 2"

        success2 = deliver_inbound_message(addr1, parsed_email_2, raw_email_2)
        assert success2 is True
        assert models.Thread.objects.filter(accesses__mailbox=mailbox1).count() == 1
        assert models.Thread.objects.filter(accesses__mailbox=mailbox2).count() == 1
        thread1 = models.Thread.objects.get(accesses__mailbox=mailbox1)
        assert thread1.messages.count() == 1
        message2 = thread1.messages.first()
        assert message2.mime_id == parsed_email_2["message_id"]
        assert thread1.subject == f"Re: {subject}"

        # 3. user1 -> user2 (Reply to Reply)
        parsed_email_3 = {
            "subject": f"Re: {subject}",
            "from": {"name": "User One", "email": addr1},
            "to": [{"name": "User Two", "email": addr2}],
            "textBody": [{"content": "You are welcome!"}],
            "message_id": "msg3.part3.rereply@exchange.test",
            "in_reply_to": message2.mime_id,  # Link to user2's reply
            "headers": {
                "references": f"<{message1.mime_id}> <{message2.mime_id}>"
            },  # Full chain
            "date": timezone.now(),
        }
        raw_email_3 = b"Raw for message 3"

        success3 = deliver_inbound_message(addr2, parsed_email_3, raw_email_3)
        assert success3 is True
        # Counts should remain 1 thread per mailbox
        assert models.Thread.objects.filter(accesses__mailbox=mailbox1).count() == 1
        assert models.Thread.objects.filter(accesses__mailbox=mailbox2).count() == 1

        # Verify message3 landed in thread2
        thread1.refresh_from_db()
        thread2.refresh_from_db()
        assert thread1.messages.count() == 1  # Still just message 2
        assert thread2.messages.count() == 2  # Now message 1 and message 3
        message3 = thread2.messages.exclude(id=message1.id).first()
        assert thread2.subject == subject  # Make sure the original subject is kept
        assert message3.mime_id == parsed_email_3["message_id"]

    def test_deliver_message_with_empty_subject(self, target_mailbox, raw_email_data):
        """Test delivery of message with empty subject."""
        recipient_addr = f"{target_mailbox.local_part}@{target_mailbox.domain.name}"

        # Create parsed email with empty subject
        parsed_email_empty_subject = {
            "subject": "",  # Empty subject
            "from": {"name": "Test Sender", "email": "sender@test.com"},
            "to": [{"name": "Recipient Name", "email": recipient_addr}],
            "cc": [],
            "bcc": [],
            "textBody": [{"content": "Test body content."}],
            "message_id": "test.empty.subject@example.com",
            "date": timezone.now(),
        }

        success = deliver_inbound_message(
            recipient_addr, parsed_email_empty_subject, raw_email_data
        )

        assert success is True
        assert models.Message.objects.count() == 1
        assert models.Thread.objects.count() == 1

        message = models.Message.objects.first()
        thread = models.Thread.objects.first()

        # Verify message and thread have empty subject
        assert message.subject == ""
        assert thread.subject == ""
        assert message.thread == thread
        assert str(message) == "(no subject)"
        assert str(thread) == "(no subject)"

    def test_deliver_message_with_null_subject(self, target_mailbox, raw_email_data):
        """Test delivery of message with null subject."""
        recipient_addr = f"{target_mailbox.local_part}@{target_mailbox.domain.name}"

        # Create parsed email with null subject
        parsed_email_null_subject = {
            "subject": None,  # Null subject
            "from": {"name": "Test Sender", "email": "sender@test.com"},
            "to": [{"name": "Recipient Name", "email": recipient_addr}],
            "cc": [],
            "bcc": [],
            "textBody": [{"content": "Test body content."}],
            "message_id": "test.null.subject@example.com",
            "date": timezone.now(),
        }

        success = deliver_inbound_message(
            recipient_addr, parsed_email_null_subject, raw_email_data
        )

        assert success is True
        assert models.Message.objects.count() == 1
        assert models.Thread.objects.count() == 1

        message = models.Message.objects.first()
        thread = models.Thread.objects.first()

        # Verify message and thread have null subject
        assert message.subject is None
        assert thread.subject is None
        assert message.thread == thread
        assert str(message) == "(no subject)"
        assert str(thread) == "(no subject)"

    def test_deliver_message_without_subject_field(
        self, target_mailbox, raw_email_data
    ):
        """Test delivery of message without subject field."""
        recipient_addr = f"{target_mailbox.local_part}@{target_mailbox.domain.name}"

        # Create parsed email without subject field
        parsed_email_no_subject = {
            # No subject field
            "from": {"name": "Test Sender", "email": "sender@test.com"},
            "to": [{"name": "Recipient Name", "email": recipient_addr}],
            "cc": [],
            "bcc": [],
            "textBody": [{"content": "Test body content."}],
            "message_id": "test.no.subject@example.com",
            "date": timezone.now(),
        }

        success = deliver_inbound_message(
            recipient_addr, parsed_email_no_subject, raw_email_data
        )

        assert success is True
        assert models.Message.objects.count() == 1
        assert models.Thread.objects.count() == 1

        message = models.Message.objects.first()
        thread = models.Thread.objects.first()

        # Verify message and thread have null subject (default behavior)
        assert message.subject is None
        assert thread.subject is None
        assert message.thread == thread
        assert str(message) == "(no subject)"
        assert str(thread) == "(no subject)"

    def test_deliver_message_with_very_long_subject(
        self, target_mailbox, raw_email_data
    ):
        """Test delivery of message with subject exceeding max_length."""
        recipient_addr = f"{target_mailbox.local_part}@{target_mailbox.domain.name}"

        # Create parsed email with very long subject
        long_subject = "A" * 256  # Exceeds max_length of 255
        parsed_email_long_subject = {
            "subject": long_subject,
            "from": {"name": "Test Sender", "email": "sender@test.com"},
            "to": [{"name": "Recipient Name", "email": recipient_addr}],
            "cc": [],
            "bcc": [],
            "textBody": [{"content": "Test body content."}],
            "message_id": "test.long.subject@example.com",
            "date": timezone.now(),
        }

        # This should fail due to max_length constraint
        success = deliver_inbound_message(
            recipient_addr, parsed_email_long_subject, raw_email_data
        )
        assert success is False
        assert models.Message.objects.count() == 0

    def test_thread_subject_consistency_with_empty_subject(
        self, target_mailbox, raw_email_data
    ):
        """Test that thread subject is consistent when messages have empty subjects."""
        recipient_addr = f"{target_mailbox.local_part}@{target_mailbox.domain.name}"

        # First message with empty subject
        parsed_email_1 = {
            "subject": "",
            "from": {"name": "Sender 1", "email": "sender1@test.com"},
            "to": [{"name": "Recipient", "email": recipient_addr}],
            "textBody": [{"content": "First message."}],
            "message_id": "msg1.empty@example.com",
            "date": timezone.now(),
        }

        success1 = deliver_inbound_message(
            recipient_addr, parsed_email_1, raw_email_data
        )
        assert success1 is True

        # Second message with empty subject (should join same thread)
        parsed_email_2 = {
            "subject": "",
            "from": {"name": "Sender 2", "email": "sender2@test.com"},
            "to": [{"name": "Recipient", "email": recipient_addr}],
            "textBody": [{"content": "Second message."}],
            "message_id": "msg2.empty@example.com",
            "in_reply_to": "msg1.empty@example.com",
            "date": timezone.now(),
        }

        success2 = deliver_inbound_message(
            recipient_addr, parsed_email_2, raw_email_data
        )
        assert success2 is True

        # Verify both messages are in the same thread with empty subject
        assert models.Thread.objects.count() == 1
        thread = models.Thread.objects.first()
        assert thread.subject == ""
        assert thread.messages.count() == 2

        messages = thread.messages.all()
        assert messages[0].subject == ""
        assert messages[1].subject == ""
