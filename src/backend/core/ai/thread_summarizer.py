
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from core.models import Thread
from typing import Optional

from core.services.ai_service import AIService


@dataclass
class Message:
    datetime: str
    sender: str
    recipients: List[str]
    id: str = field(default_factory=uuid.uuid4)
    cc: List[str] = field(default_factory=list)
    subject: str = ""
    body: str = ""
    attachments: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    summary: str = ""

    def __str__(self):
        return (
            f"Message ID: {self.id}\n"
            f"De: {self.sender}\n"
            f"À: {', '.join(self.recipients)}\n"
            f"CC: {', '.join(self.cc)}\n"
            f"Date: {self.datetime}\n"
            f"Sujet: {self.subject}\n\n"
            f"{self.body}"
        )


from typing import Dict, Any

def get_message_from_parsed_mime_data(data: Dict[str, Any]) -> Message:
    # Datetime (ISO8016 format)
    date_str = data.get('date')
    if isinstance(date_str, (datetime,)):
        date_str = date_str.isoformat()
    else:
        date_str = str(date_str) if date_str else ""

    # Sender "Name <email>" or just email
    sender_name = data.get('from', {}).get('name', "")
    sender_email = data.get('from', {}).get('email', "")
    sender = f"{sender_name} <{sender_email}>" if sender_name else sender_email

    # Recipients list, "Name <email>" or just email
    to_list = data.get('to', [])
    recipients = []
    for r in to_list:
        name = r.get('name', "")
        email_addr = r.get('email', "")
        recipients.append(f"{name} <{email_addr}>" if name else email_addr)

    # CC 
    cc_list = data.get('cc', [])
    cc = []
    for c in cc_list:
        name = c.get('name', "")
        email_addr = c.get('email', "")
        cc.append(f"{name} <{email_addr}>" if name else email_addr)

    # Subject
    subject = data.get('subject', 'Aucun objet')

    # Body
    body = ""
    for part in data.get('textBody', []):
        if part.get('type') == 'text/plain':
            body = part.get('content', "")
            break

    # Message-ID
    msg_id = data.get('message_id', str(datetime.now().timestamp()))

    return Message(
        datetime=date_str,
        sender=sender,
        recipients=recipients,
        cc=cc,
        subject=subject,
        body=body,
        id=msg_id,
        attachments=data.get('attachments', []),
    )


def get_messages_from_thread(thread: Thread) -> List[Message]:
    """
    Extract messages from a thread and return them as a list of Message objects before summarizing.
    """
    messages = []
    for message in thread.messages.all():
        if not (message.is_draft or message.is_trashed):
            parsed_data = message.get_parsed_data()
            if parsed_data:
                msg = get_message_from_parsed_mime_data(parsed_data)
                msg.id = str(message.id)
                messages.append(msg)
    return messages


def count_tokens_in_messages(messages: List[Message]) -> int:
    """
    Counts the number of tokens in a list of messages.
    Args:
        messages (List[Message]): List of Message objects.
    Returns:
        int: Total number of tokens in the messages.
    """
    token_count = 0
    for message in messages:
        # Count tokens in the subject and body
        token_count += len(message.subject.split())
        token_count += len(message.body.split())
    return token_count


def summarize_thread(thread: Thread, language: str="fr") -> str:
    """
    Summarizes a thread using the OpenAI client.
    Args:
        thread (Thread): Thread to summarize.
    Returns:
        str: Summary of the thread.
    """

    # Extract messages from the thread
    messages = get_messages_from_thread(thread)

    # Prepare the prompt for the AI model
    conversation_text = "\n\n".join([str(message) for message in messages])
    prompt_query = "Tu es un assistant intelligent qui résume des boucles de mails. Tu dois résumer le contenu de la conversation en une ou deux lignes maximum sans préciser 'Résumé:'. Si des liens importants apparaissent dans les emails, tu dois les mentionner dans le résumé de façon claire en Markdown et intégré au résumé et sinon ne pas les mentionner."
    prompt = prompt_query + conversation_text + f"\n\nRésumé Markdown dans la langue '{language}' des emails ci-dessus :\n"
    
    # Make the API call to get the summary
    summary = AIService().call_ai_api(prompt)
    return summary



