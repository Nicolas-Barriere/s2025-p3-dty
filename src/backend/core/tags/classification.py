import json
from .tools import get_prompt
import os
from core.services.ai_services import AIService


# Clear le terminal au lancement du script
os.system("cls" if os.name == "nt" else "clear")


def func(message):
    return "Bonjour Fabian!"


def classify_single_emails(single_emails: str) -> dict[str, str | str]:
    """
    Takes a string representing a list of single emails. Each email must have an ID.
    The input can be any format comprehensible my the LLM, such as a JSON string or a list of Email objects.
    Giving too many emails at once may lead to an error as the LLM might make a mistake and forget an email.
    Returns a list of dictionaries with the email ID, tag, and explanation for each email.
    """
    print("FUNCTION CALLED: classify_single_emails")
    print(single_emails)
    prompt_mail_solo = get_prompt("prompt_solo")

    response = AIService().call_ai_api(prompt_mail_solo + single_emails)
    ans = []
    for line in response.splitlines():
        if not line.strip():
            continue

        try:
            id, end = line.split("---")
            tags, explanation = end.split("(", maxsplit=1)
            tags = tags.strip().split(",")

        except Exception as e:
            print("ERROR:", line, response, e, "END ERROR")
            raise ValueError(
                "Line format is incorrect. Expected 'id: tag (explanation)' format."
            )
        explanation = explanation.strip(")")
        ans.append({"id": id.strip(), "tags": tags, "explanation": explanation})

    return ans


def classify_email_conversation(email_conversation: str) -> tuple[str, str, str]:
    prompt_mails_conv = get_prompt("prompt_conv")

    return AIService().call_ai_api(prompt_mails_conv + email_conversation)


def save_classification(classification: list[dict]) -> None:
    """
    Save the classification results to a JSON file.
    """
    print("Hello !")

    for email in classification:
        email["tag"] = [email["tag"]]
        email["explanation"] = [email["explanation"]]

    file_path = "data/classification_results.json"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read().strip()
            if content:
                emails = json.loads(content)
            else:
                emails = []
    else:
        emails = []

    id_to_email = {email["id"]: email for email in emails}
    for email in classification:
        if email["id"] in id_to_email:
            id_to_email[email["id"]]["tag"].append(email["tag"][0])
            id_to_email[email["id"]]["explanation"].append(email["explanation"][0])
        else:
            emails.append(email)

    # Enregistrer le résultat
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(emails, file, indent=4, ensure_ascii=False)
