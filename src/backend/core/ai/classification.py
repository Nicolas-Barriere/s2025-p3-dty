import json
from core.services.ai_service import AIService
import yaml
import os
from datetime import datetime


def get_prompt(prompt_name: str) -> str:
    """
    Loads the prompt text for the given prompt name from the prompts.yaml file
    located in the same directory as this script.
    """

    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompts_path = os.path.join(current_dir, "prompts.yaml")
    with open(prompts_path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    return data.get("prompts", {})[prompt_name]


def get_most_relevant_labels(single_emails: list, labels: list) -> list[str]:
    """
    Classifies the given email(s) into the most relevant labels using an AI service.

    Args:
        single_emails (list): A list of Message objects to classify.
        labels (list): A list of label dictionaries with 'name' and 'description'.

    Returns:
        list[str]: A list with the labels to which the email(s) belong.
    """
    # Extract all message content as formatted text strings
    emails_data = []
    for msg in single_emails:
        try:
            # Use the get_as_text() method which already formats everything nicely
            message_text = msg.get_as_text()
            print(f"FABIAN AI MESSAGE TEXT: {message_text}")
            emails_data.append(message_text)
        except Exception as e:
            print(f"Error getting message text: {e}")
            # Fallback to basic info if get_as_text() fails
            subject = getattr(msg, "subject", "") or "No subject"
            sender = str(msg.sender) if msg.sender else "Unknown sender"
            emails_data.append(f"Subject: {subject}\nFrom: {sender}")

    # Combine all emails into one text block
    all_emails_text = "\n\n---MESSAGE SEPARATOR---\n\n".join(emails_data)

    prompt: str = get_prompt("prompt_labels")
    labels = [
        {k: v for k, v in label.items() if k in ("name", "description")}
        for label in labels
    ]
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " +00:00"
    final_prompt = (
        prompt.replace("[THREAD_EMAILS]", all_emails_text)
        .replace("[LABELS]", str(labels))
        .replace("[DATE_TIME]", current_datetime)
    )

    response = AIService().call_ai_api(final_prompt)

    return json.loads(response)
