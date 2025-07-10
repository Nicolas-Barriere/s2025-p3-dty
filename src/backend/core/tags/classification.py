import json
from .tools import get_prompt
from core.services.ai_services import AIService


def get_most_relevant_labels(single_emails: str, labels: list) -> dict[str, str | str]:
    """
    Takes a string representing a list of single emails. Each email must have an ID.
    The input can be any format comprehensible my the LLM, such as a JSON string or a list of Email objects.
    Giving too many emails at once may lead to an error as the LLM might make a mistake and forget an email.
    Returns a list of dictionaries with the email ID, tag, and explanation for each email.
    """
    print("FUNCTION CALLED: classify_single_emails")
    print(single_emails)
    prompt_mail_solo: str = get_prompt("prompt_solo")

    response = AIService().call_ai_api(
        prompt_mail_solo.replace("[THREAD_EMAILS]", str(single_emails)).replace(
            "[LABELS]", str(labels)
        )
    )

    print(f"FABIAN RESPONSE FROM LLM: {response}")
    return json.loads(response)
