import json
from core.services.ai_service import AIService
import yaml
from typing import Dict
import os


def get_prompt(prompt_name: str) -> Dict[str, str]:
    """
    Load prompts from a YAML file.

    Parameters:
        file_path (str): Path to the YAML file.

    Returns:
        Dict[str, str]: Dictionary with prompt names as keys and their text content as values.
    """

    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompts_path = os.path.join(current_dir, "prompts.yaml")
    with open(prompts_path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    return data.get("prompts", {})[prompt_name]


def get_most_relevant_labels(single_emails: str, labels: list) -> dict[str, str | str]:
    """
    Takes a string representing a list of single emails. Each email must have an ID.
    The input can be any format comprehensible my the LLM, such as a JSON string or a list of Email objects.
    Giving too many emails at once may lead to an error as the LLM might make a mistake and forget an email.
    Returns a list of dictionaries with the email ID, tag, and explanation for each email.
    """
    prompt_mail_solo: str = get_prompt("prompt_solo")

    response = AIService().call_ai_api(
        prompt_mail_solo.replace("[THREAD_EMAILS]", str(single_emails)).replace(
            "[LABELS]", str(labels)
        )
    )

    return json.loads(response)
