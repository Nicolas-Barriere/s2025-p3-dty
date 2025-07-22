import json
from core.services.ai_service import AIService
from datetime import datetime
from pathlib import Path
from core.ai.utils import get_messages_from_thread
from core.models import Thread


def get_most_relevant_labels(
    thread: Thread, labels: list, language: str = "fr"
) -> list[str]:
    """
    Classifies the given email(s) into the most relevant labels using an AI service.
    """

    # Extract messages from the thread
    messages = get_messages_from_thread(thread)
    messages_as_text = "\n\n".join([message.get_as_text() for message in messages])

    # Prepare labels for the prompt
    labels = [
        {k: v for k, v in label.items() if k in ("name", "description")}
        for label in labels
    ]

    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " +00:00"

    # Load the prompt template from ai_prompts.json
    prompts_path = Path(__file__).parent / "ai_prompts.json"
    with open(prompts_path, encoding="utf-8") as f:
        prompts = json.load(f)

    # Get the appropriate prompt template based on the language
    prompt_template = prompts.get(
        language, prompts["fr"]
    )  # Fallback to 'fr' if not found
    prompt_query = prompt_template["classification_query"]
    prompt = prompt_query.format(
        messages=messages_as_text,
        labels=labels,
        date_time=current_datetime,
        language=language,
    )

    # Make the API call to get the best labels
    print(f"FABIAN AI PROMPT: {prompt}")
    best_labels = AIService().call_ai_api(prompt)
    print(f"FABIAN AI BEST LABELS: {best_labels}")

    return json.loads(best_labels)
