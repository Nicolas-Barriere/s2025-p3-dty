
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from core.models import Thread

from core.services.ai_services import AIService


@dataclass
class Message:
    datetime: str
    sender: str
    recipients: List[str]
    id: str = field(default_factory=lambda: str(datetime.now().timestamp()))
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
        parsed_data = message.get_parsed_data()
        if parsed_data:
            msg = get_message_from_parsed_mime_data(parsed_data)
            msg.id = str(message.id)
            messages.append(msg)
    return messages


def summarize_thread(thread: Thread) -> str:
    """
    Summarizes a thread using the ALBERT model.
    Args:
        thread (Thread): Thread to summarize.
    Returns:
        str: Summary of the thread.
    """

    # Prepare the prompt for the AI model
    messages = get_messages_from_thread(thread)
    conversation_text = "\n\n".join([str(message) for message in messages])
    prompt_query = "Tu es un assistant intelligent qui résume les emails. Tu dois fournir un résumé concis, sous forme de bullet points clairs, des emails suivants qui forment une conversation cohérente et prendre en compte le contexte avec les destinataires et les copies. Ta réponse doit être la plus concise possible et ne pas repréciser les informations du mails (destinataires, ...). En cas de détection de SPAM ta réponse doit être précédée de la mention 'POTENTIEL SPAM DÉTECTÉ'"
    prompt = prompt_query + conversation_text + "\n\nRésumé en français des emails ci-dessus :"
    
    # Make the API call to get the summary
    summary = AIService().call_ai_api(prompt)
    return summary


def generate_answer(thread: Thread) -> str:
    """
    Generates an answer to a thread using the ALBERT model.
    Args:
        thread (Thread): Thread to answer.
    Returns:
        str: Answer to the thread.
    """

    # Prepare the prompt for the AI model
    messages = get_messages_from_thread(thread)
    conversation_text = "\n\n".join([str(message) for message in messages])
    prompt_query = "Tu es un assistant intelligent qui génère une réponse à des mails. Tu dois fournir une réponse aux emails suivants qui forment une conversation cohérente et prendre en compte le contexte avec les destinataires et les copies. Ta réponse doit être la plus concise possible et ne pas repréciser les informations du mails (destinataires, ...). En cas de détection de SPAM ta réponse doit être précédée de la mention 'POTENTIEL SPAM DÉTECTÉ'"
    prompt = prompt_query + conversation_text + "\n\nRéponse en français aux emails ci-dessus :"
    
    # Make the API call to get the summary
    answer = AIService().call_ai_api(prompt)
    return answer


