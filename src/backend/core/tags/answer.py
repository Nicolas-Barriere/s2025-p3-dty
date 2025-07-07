from email_class import Email
from llm import call_llm_with_new_prompt
import json
from colorama import Fore, Style
from tools import get_prompt


def generate_3_answer(email_info: str) -> dict:
    """
    Generate an answer for a given email.
    Args:
        email (Email): The email object containing the details of the email.
    Returns:
        str: The generated answer for the email.
    """
    generate_3_answers_prompt = get_prompt("prompt_3_answers")
    answer = call_llm_with_new_prompt(generate_3_answers_prompt + str(email_info))
    json_str = answer.split("```json")[1].split("```")[0].strip()
    possible_answers = json.loads(json_str)
    return possible_answers


def generate_answer_from_prompt(user_prompt: str, email_info: str) -> dict:
    generate_answer_from_user_prompt = get_prompt("prompt_answer_from_user")
    prompt = generate_answer_from_user_prompt.replace("[[EMAIL]]", str(email_info))
    prompt = prompt.replace("[[USER PROMPT]]", user_prompt)
    answer = call_llm_with_new_prompt(prompt)
    return answer


if __name__ == "__main__":
    email = Email(
        datetime="2025-06-07 09:00:00",
        sender="sophie@marketing.org",
        recipients=["arnaud@logistique.net"],
        subject="Point sur la campagne de juin",
        cc=["chef.projet@marketing.org"],
        body="Bonjour Arnaud,\nPeux-tu me confirmer que les affiches seront livrées avant le 12 juin ?\nC’est crucial pour le lancement national.\nMerci d’avance,\nSophie",
    )

    email_conv = [
        {
            "datetime": "2025-06-18 16:30:00",
            "sender": "romain@formation.edu",
            "recipients": ["etudiants@master.univ.fr"],
            "subject": "Report du cours de jeudi",
            "body": "Chers étudiants,\nEn raison d'un imprévu, le cours de jeudi à 14h est reporté à vendredi à la même heure.\nLe programme reste inchangé : révisions pour l'examen final.\nCordialement,\nProfesseur Romain Dubois",
            "cc": ["responsable.pedagogique@formation.edu"],
        },
        {
            "datetime": "2025-06-18 17:15:00",
            "sender": "sarah.moreau@master.univ.fr",
            "recipients": ["romain@formation.edu"],
            "subject": "Re: Report du cours de jeudi",
            "body": "Bonjour Professeur,\nMerci pour l'information. Pourrions-nous avoir les derniers supports de cours avant vendredi ?\nBonne soirée,\nSarah Moreau",
            "cc": ["responsable.pedagogique@formation.edu"],
        },
    ]

    EMAILS = email
    USER_PROMPT = """
    Il y a du retard. Affiches livrées le 20 juin. Impossible avant. C'est ok ?
    """

    possible_answers = generate_3_answer(EMAILS)
    for answer in possible_answers:
        for key, value in answer.items():
            if key == "summary":
                print(
                    f"{Fore.CYAN}{key}:{Style.RESET_ALL} {Fore.YELLOW}{value}{Style.RESET_ALL}"
                )
            elif key == "response":
                print(
                    f"{Fore.GREEN}{key}:{Style.RESET_ALL} {Fore.WHITE}{value}{Style.RESET_ALL}"
                )
            else:
                print(
                    f"{Fore.WHITE}{key}:{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}{value}{Style.RESET_ALL}"
                )

    answer_from_prompt = generate_answer_from_prompt(USER_PROMPT, EMAILS)
    print(answer_from_prompt)
