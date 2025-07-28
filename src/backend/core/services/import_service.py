"""Service layer for importing messages via EML, MBOX, or IMAP."""

import logging
from typing import Any, Dict, Optional, Tuple

from django.contrib import messages
from django.http import HttpRequest

from core.models import Blob, Mailbox
from core.tasks import (
    import_imap_messages_task,
    process_eml_file_task,
    process_mbox_file_task,
)

logger = logging.getLogger(__name__)


class ImportService:
    """Service for handling message imports."""

    @staticmethod
    def import_file(
        file: Blob,
        recipient: Mailbox,
        user: Any,
        request: Optional[HttpRequest] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Import messages from an EML or MBOX file.

        Args:
            file: The uploaded file (EML or MBOX)
            recipient: The recipient mailbox
            user: The user performing the import
            request: Optional HTTP request for admin messages

        Returns:
            Tuple of (success, response_data)
        """
        # Check user has access to mailbox in case of non superuser
        if not user.is_superuser and not recipient.accesses.filter(user=user).exists():
            return False, {"detail": "You do not have access to this mailbox."}

        try:
            file_content = file.get_content()
            content_type = file.content_type

            # Check MIME type for MBOX
            if content_type in [
                "application/octet-stream",
                "text/plain",
                "application/mbox",
            ]:
                # Process MBOX file asynchronously
                task = process_mbox_file_task.delay(file_content, str(recipient.id))
                response_data = {"task_id": task.id, "type": "mbox"}
                if request:
                    messages.info(
                        request,
                        f"Started processing MBOX file for recipient {recipient}. "
                        "This may take a while. You can check the status in the Celery task monitor.",
                    )
                return True, response_data
            # Check MIME type for EML
            elif content_type in ["message/rfc822", "application/eml"]:
                # Process EML file asynchronously
                task = process_eml_file_task.delay(file_content, str(recipient.id))
                response_data = {"task_id": task.id, "type": "eml"}
                if request:
                    messages.info(
                        request,
                        f"Started processing EML file for recipient {recipient}. "
                        "This may take a while. You can check the status in the Celery task monitor.",
                    )
                return True, response_data
            else:
                return False, {
                    "detail": (
                        "Invalid file format. Only EML (message/rfc822) and MBOX "
                        "(application/octet-stream, application/mbox, or text/plain) files are supported. "
                        "Detected content type: {content_type}"
                    ).format(content_type=content_type)
                }
        except Exception as e:
            logger.exception("Error processing file: %s", e)
            if request:
                messages.error(request, f"Error processing file: {str(e)}")

            return False, {"detail": str(e)}

    @staticmethod
    def import_imap(
        imap_server: str,
        imap_port: int,
        username: str,
        password: str,
        recipient: Mailbox,
        user: Any,
        use_ssl: bool = True,
        request: Optional[HttpRequest] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Import messages from an IMAP server.

        Args:
            imap_server: IMAP server hostname
            imap_port: IMAP server port
            username: Email address for login
            password: Password for login
            recipient: The recipient mailbox
            user: The user performing the import
            use_ssl: Whether to use SSL
            request: Optional HTTP request for admin messages

        Returns:
            Tuple of (success, response_data)
        """
        # Check user has access to mailbox in case of non superuser
        if not user.is_superuser and not recipient.accesses.filter(user=user).exists():
            return False, {"detail": "You do not have access to this mailbox."}

        try:
            # Start the import task
            task = import_imap_messages_task.delay(
                imap_server=imap_server,
                imap_port=imap_port,
                username=username,
                password=password,
                use_ssl=use_ssl,
                recipient_id=str(recipient.id),
            )
            response_data = {"task_id": task.id, "type": "imap"}
            if request:
                messages.info(
                    request,
                    f"Started importing messages from IMAP server for recipient {recipient}. "
                    "This may take a while. You can check the status in the Celery task monitor.",
                )
            return True, response_data

        except Exception as e:
            logger.exception("Error starting IMAP import: %s", e)
            if request:
                messages.error(request, f"Error starting IMAP import: {str(e)}")
            return False, {"detail": str(e)}
