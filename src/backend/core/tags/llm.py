# import openai
# from dotenv import load_dotenv
# import os

# load_dotenv()

# openai.api_base = "https://albert.api.etalab.gouv.fr/v1"
# openai.api_key = os.getenv("ALBERT_API_KEY")
# assert openai.api_key is not None, "ALBERT_API_KEY must be set in the .env file"


# data = {
#     "model": "albert-large",
#     "stream": False,
#     "messages": [],
#     "n": 1,
# }


# def call_llm_with_new_prompt(prompt: str) -> str:
#     """
#     Call the LLM with a new prompt and return the response.
#     Args:
#         prompt (str): The prompt to send to the LLM.
#     Returns:
#         str: The response from the LLM.
#     """
#     # data["messages"] = [{"role": "user", "content": prompt}]
#     # response_obj = client.chat.completions.create(**data)
#     # response = response_obj.choices[0].message.content
#     response = openai.ChatCompletion.create(
#         model="albert-large",
#         messages=[{"role": "user", "content": prompt}],
#     )
#     return response["choices"][0]["message"]["content"]
