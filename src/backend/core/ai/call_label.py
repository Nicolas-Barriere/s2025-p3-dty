from core.ai.thread_classifier import get_most_relevant_labels
from core.ai.thread_summarizer import get_messages_from_thread
from core.models import Label, Mailbox, Thread, User


def list_labels_of_user(user, mailbox_id):
    """Get all labels for a user in a specific mailbox."""
    return Label.objects.filter(mailbox_id=mailbox_id).values()


def create_label(mailbox_id, user, label_name: str, color: str):
    """Create a new label."""
    mailbox = Mailbox.objects.get(id=mailbox_id)
    label = Label.objects.create(
        name=label_name,
        mailbox=mailbox,
        color=color,
    )
    return label


def add_thread_to_label(label_id, thread_id):
    """Add a thread to a label."""
    try:
        label = Label.objects.get(id=label_id)
        thread = Thread.objects.get(id=thread_id)
        label.threads.add(thread)
        return True
    except (Label.DoesNotExist, Thread.DoesNotExist):
        return False


def assign_label_to_thread(thread: Thread, mailbox_id):
    """Assign relevant labels to a thread based on AI classification."""
    # Get recipients from the last message
    last_message = get_messages_from_thread(thread)[-1]
    recipients = last_message.recipients.select_related("contact").all()

    # Get the email from the first recipient's contact
    recipient_email = recipients[0].contact.email

    user = User.objects.get(email=recipient_email)

    labels = list_labels_of_user(user, mailbox_id)
    best_labels = get_most_relevant_labels(thread, labels)

    for label_name in best_labels:
        # Plus efficace : chercher le label une seule fois
        matching_label = next(
            (label for label in labels if label["name"] == label_name), None
        )

        if matching_label and matching_label["is_auto"]:
            add_thread_to_label(
                label_id=matching_label["id"],
                thread_id=thread.id,
            )
