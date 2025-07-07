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
