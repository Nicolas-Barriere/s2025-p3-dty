from rest_framework.test import APIRequestFactory, force_authenticate
from core.api.viewsets.label import LabelViewSet
from core.models import User
from core import factories
from core.ai.thread_summarizer import get_messages_from_thread
from core.ai.thread_classifier import get_most_relevant_labels
from core.models import Thread
from django.db.models import Exists, OuterRef
from core.models import Label, MailboxAccess


def list_labels_of_user(factory, user, mailbox_id):
    response = Label.objects.filter(mailbox_id=mailbox_id).distinct()
    return response.values()


def create_label(factory, mailbox_id, user, label_name: str, color: str):
    data = {
        "name": label_name,
        "mailbox": mailbox_id,
        "color": color,
    }

    request = factory.post("/api/labels/", data, format="json")

    force_authenticate(request, user=user)

    view = LabelViewSet.as_view({"post": "create"})
    response = view(request)
    return response


def add_thread_to_label(factory, mailbox_id, user, label_id, thread_id):
    request = factory.post(
        f"/api/labels/{label_id}/add-threads/",
        {"thread_ids": [thread_id]},
        format="json",
    )

    force_authenticate(request, user=user)

    view = LabelViewSet.as_view({"post": "add_threads"})
    response = view(request, pk=label_id)
    return response


def assign_label_to_thread(thread: Thread, mailbox_id):
    factory = APIRequestFactory()

    # Get recipients from the last message
    last_message = get_messages_from_thread(thread)[-1]
    recipients = last_message.recipients.select_related("contact").all()

    if not recipients:
        print("No recipients found for the message")
        return

    # Get the email from the first recipient's contact
    recipient_email = recipients[0].contact.email

    user = User.objects.get(email=recipient_email)

    labels = list_labels_of_user(factory, user, mailbox_id)
    best_labels = get_most_relevant_labels(thread, labels)

    for label_name in best_labels:
        label_id = list(filter(lambda x: x["name"] == label_name, labels))[0]["id"]
        is_enabled = list(filter(lambda x: x["name"] == label_name, labels))[0][
            "is_enabled"
        ]

        if is_enabled:
            response = add_thread_to_label(
                factory,
                mailbox_id,
                user,
                label_id=label_id,
                thread_id=thread.id,
            )
